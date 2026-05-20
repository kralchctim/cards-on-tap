"""
search.py — Scryfall-style search parser for tak.db
=====================================================
Parses Scryfall search syntax and translates it to SQLite queries
against the tak.db schema.

SUPPORTED:
  name:, n:           Card name (partial match)
  o:, oracle:         Oracle text (partial match)
  t:, type:           Type line (partial match)
  c:, color:          Colour filter (WUBRG, guild/shard/wedge names, m, c)
  id:, identity:      Colour identity filter (same values as c:)
  m:, mana:           Mana cost (partial match, e.g. m:{G}{U})
  mv:, manavalue:,    Mana value / CMC (numeric, supports >, <, >=, <=, =, !=)
  cmc:
  pow:, power:        Power (numeric comparison, or pow>tou)
  tou:, toughness:    Toughness (numeric comparison)
  pt:, powtou:        Total power + toughness (numeric)
  kw:, keyword:       Keyword ability (e.g. kw:flying)
  f:, format:         Format legality (e.g. f:commander)
  banned:             Banned in format
  restricted:         Restricted in format
  r:, rarity:         Rarity (common/uncommon/rare/mythic, supports >, <, >=)
  s:, e:, set:        Set code (e.g. e:war)
  cn:, number:        Collector number (numeric comparison supported)
  a:, artist:         Artist name (partial match)
  date:               Release date (YYYY-MM-DD or YYYY, supports >, <, etc.)
  year:               Release year (supports >, <, >=, <=, =)
  tag:                Custom tag (your tak.db tags)
  is:foil             Has foil printing
  is:nonfoil          Has nonfoil printing
  is:etched           Has etched foil printing
  is:digital          Arena/MTGO only card
  is:permanent        Not an instant or sorcery
  is:spell            Instant or sorcery
  is:historic         Legendary, artifact, or saga
  is:vanilla          No oracle text or keywords
  is:commander        Legendary creature (can be commander)
  is:brawler          Legendary creature or planeswalker
  is:multicolor       More than one colour
  is:colorless        No colours
  is:reprint          Printed in more than one set
  is:unique           Only printed in one set
  not:X               Inverse of is:X
  !name               Exact card name match
  "phrase"            Phrase appears in name or oracle text
  -keyword:value      Negate any condition
  OR                  Logical OR between groups
  (...)               Group conditions

NOT SUPPORTED (no data in tak.db):
  ft:, flavor:        Flavour text
  usd:, eur:, tix:   Prices
  wm:, watermark:    Watermarks
  cube:               Cube lists
  art:, atag:         Art tagger tags
  function:, otag:   Oracle tagger tags
  border:, frame:     Frame/border type
  b:, block:          Block membership
  lang:               Language
  in:                 Historical set membership
  loy:, loyalty:      Starting loyalty (no loyalty column)
  ft:, flavor:        Flavour text (no column)
  unique:, display:,  Display/sort keywords (silently ignored)
  order:, prefer:,
  direction:
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional, Union


# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────

_COLOUR_LETTERS = {'w': 'W', 'u': 'U', 'b': 'B', 'r': 'R', 'g': 'G'}
_COLOUR_NAMES   = {'white': 'W', 'blue': 'U', 'black': 'B', 'red': 'R', 'green': 'G'}

_COLOUR_ALIASES: dict[str, str] = {
    # Guilds
    'azorius': 'WU',   'dimir': 'UB',    'rakdos': 'BR',   'gruul': 'RG',
    'selesnya': 'GW',  'orzhov': 'WB',   'izzet': 'UR',    'golgari': 'BG',
    'boros': 'RW',     'simic': 'GU',
    # Shards
    'bant': 'GWU',     'esper': 'WUB',   'grixis': 'UBR',
    'jund': 'BRG',     'naya': 'RGW',
    # Wedges
    'abzan': 'WBG',    'jeskai': 'URW',  'sultai': 'BGU',
    'mardu': 'RWB',    'temur': 'GUR',
    # Four-colour
    'chaos': 'UBRG',   'aggression': 'WBRG', 'altruism': 'WURG',
    'growth': 'WUBG',  'artifice': 'WUBR',
    # Five-colour
    'rainbow': 'WUBRG', 'fivecolor': 'WUBRG', 'fivecolour': 'WUBRG',
    # Strixhaven colleges
    'silverquill': 'WB', 'prismari': 'UR', 'witherbloom': 'BG',
    'lorehold': 'RW',    'quandrix': 'GU',
}

_VALID_FORMATS = {
    'standard', 'future', 'historic', 'timeless', 'gladiator', 'pioneer',
    'modern', 'legacy', 'pauper', 'vintage', 'penny', 'commander', 'oathbreaker',
    'standardbrawl', 'brawl', 'alchemy', 'paupercommander', 'duel', 'oldschool',
    'premodern', 'predh', 'tlr',
}

_RARITY_ORDER  = {'common': 1, 'uncommon': 2, 'rare': 3, 'mythic': 4, 'special': 5, 'bonus': 6}
_RARITY_ABBREV = {'c': 'common', 'u': 'uncommon', 'r': 'rare', 'm': 'mythic', 's': 'special', 'b': 'bonus'}

# These are Scryfall display/sort hints — silently ignored
_DISPLAY_KEYWORDS = {'unique', 'display', 'order', 'prefer', 'direction'}

# These we can't support — we warn the user
_UNSUPPORTED_KEYWORDS = {
    'ft', 'flavor', 'flavour', 'fulloracle', 'fo',
    'usd', 'eur', 'tix', 'cheapest',
    'wm', 'watermark',
    'cube',
    'art', 'atag', 'arttag', 'function', 'otag', 'oracletag',
    'border', 'frame',
    'b', 'block',
    'lang', 'language',
    'in',
    'loy', 'loyalty',
    'artists', 'illustrations', 'prints', 'paperprints', 'sets', 'papersets',
    'new', 'devotion', 'produces',
    'stamp', 'game',
    'has',
}

_RARITY_SQL = (
    "CASE p.rarity "
    "WHEN 'common' THEN 1 WHEN 'uncommon' THEN 2 "
    "WHEN 'rare' THEN 3 WHEN 'mythic' THEN 4 "
    "WHEN 'special' THEN 5 WHEN 'bonus' THEN 6 "
    "ELSE 0 END"
)


# ─────────────────────────────────────────────────────────────
# AST NODES
# ─────────────────────────────────────────────────────────────

@dataclass
class AndExpr:
    children: list

@dataclass
class OrExpr:
    children: list

@dataclass
class Term:
    negated: bool
    key: str      # e.g. 't', 'o', 'mv'
    op: str       # ':', '=', '>', '<', '>=', '<=', '!='
    value: str

@dataclass
class BareWord:
    negated: bool
    word: str

@dataclass
class Phrase:
    negated: bool
    phrase: str

@dataclass
class ExactName:
    name: str

AstNode = Union[AndExpr, OrExpr, Term, BareWord, Phrase, ExactName]


# ─────────────────────────────────────────────────────────────
# TOKENIZER
# ─────────────────────────────────────────────────────────────

# Matches (in priority order):
#   exact    — !name or !"name with spaces"
#   kv       — [-]keyword[op]value, where op is >=|<=|!=|>|<|=|:
#   phrase   — [-]"quoted phrase"
#   lparen   — (
#   rparen   — )
#   or       — the word OR (case-insensitive, word boundary)
#   word     — any other token (possibly negated with -)
_TOKENIZER_RE = re.compile(r'''
    (?P<exact>    !"[^"]*"  |  ![^\s"()]+          )
  | (?P<kv>      -?[A-Za-z_]+(?:>=|<=|!=|>|<|=|:)(?:"[^"]*"|[^\s()]+)  )
  | (?P<phrase>  -?"[^"]*"                         )
  | (?P<lparen>  \(                                )
  | (?P<rparen>  \)                                )
  | (?P<or>      (?<!\w)[Oo][Rr](?!\w)            )
  | (?P<word>    -?[^\s()]+                        )
''', re.VERBOSE)

_KV_RE = re.compile(r'^(-?)([A-Za-z_]+)(>=|<=|!=|>|<|=|:)(.+)$', re.DOTALL)


def _tokenize(query: str) -> list[tuple[str, str]]:
    return [(m.lastgroup, m.group()) for m in _TOKENIZER_RE.finditer(query.strip())]


# ─────────────────────────────────────────────────────────────
# RECURSIVE DESCENT PARSER
# ─────────────────────────────────────────────────────────────
# Grammar:
#   expr    ::= and_seq (OR and_seq)*
#   and_seq ::= atom+
#   atom    ::= '(' expr ')' | term
#   term    ::= EXACT | KV | PHRASE | WORD

def _parse_expr(tokens: list, pos: int) -> tuple[AstNode, int]:
    left, pos = _parse_and_seq(tokens, pos)
    or_children = [left]
    while pos < len(tokens) and tokens[pos][0] == 'or':
        pos += 1  # consume OR
        right, pos = _parse_and_seq(tokens, pos)
        or_children.append(right)
    if len(or_children) == 1:
        return or_children[0], pos
    return OrExpr(or_children), pos


def _parse_and_seq(tokens: list, pos: int) -> tuple[AstNode, int]:
    children = []
    while pos < len(tokens) and tokens[pos][0] not in ('or', 'rparen'):
        atom, pos = _parse_atom(tokens, pos)
        if atom is not None:
            children.append(atom)
    if not children:
        return AndExpr([]), pos
    if len(children) == 1:
        return children[0], pos
    return AndExpr(children), pos


def _parse_atom(tokens: list, pos: int) -> tuple[Optional[AstNode], int]:
    if pos >= len(tokens):
        return None, pos

    kind, val = tokens[pos]

    if kind == 'lparen':
        pos += 1
        node, pos = _parse_expr(tokens, pos)
        if pos < len(tokens) and tokens[pos][0] == 'rparen':
            pos += 1
        return node, pos

    elif kind == 'exact':
        pos += 1
        name = val[1:].strip('"')
        return ExactName(name), pos

    elif kind == 'kv':
        pos += 1
        m = _KV_RE.match(val)
        if not m:
            return None, pos
        neg   = m.group(1) == '-'
        key   = m.group(2).lower()
        op    = m.group(3)
        value = m.group(4).strip('"')
        return Term(neg, key, op, value), pos

    elif kind == 'phrase':
        pos += 1
        neg    = val.startswith('-')
        phrase = val.lstrip('-').strip('"')
        return Phrase(neg, phrase), pos

    elif kind == 'word':
        pos += 1
        neg  = val.startswith('-')
        word = val.lstrip('-')
        return BareWord(neg, word), pos

    else:
        return None, pos + 1


def _parse(query: str) -> AstNode:
    tokens = _tokenize(query)
    if not tokens:
        return AndExpr([])
    node, _ = _parse_expr(tokens, 0)
    return node


# ─────────────────────────────────────────────────────────────
# COLOUR UTILITIES
# ─────────────────────────────────────────────────────────────

def _resolve_colours(value: str) -> Optional[Union[list[str], str]]:
    """
    Parse a colour expression.
    Returns:
      []        — colorless
      'MULTI'   — multicolour
      ['W','U'] — list of specific colour letters
      None      — unrecognised / parse error
    """
    v = value.lower().strip()

    if v in ('c', 'colorless', 'colourless'):
        return []
    if v in ('m', 'multicolor', 'multicolour', 'multi'):
        return 'MULTI'
    if v in _COLOUR_ALIASES:
        return list(_COLOUR_ALIASES[v])
    if v in _COLOUR_NAMES:
        return [_COLOUR_NAMES[v]]

    # Parse letter-by-letter
    result: list[str] = []
    for ch in v:
        if ch in _COLOUR_LETTERS:
            c = _COLOUR_LETTERS[ch]
            if c not in result:
                result.append(c)
        else:
            return None
    return result or None


def _colour_sql(field: str, op: str, value: str) -> tuple[Optional[str], list]:
    """Generate SQL for a colour or colour_identity filter."""

    # Numeric: c=2, c>1, etc.
    try:
        n = int(value)
        op_map = {':': '>=', '=': '=', '>': '>', '<': '<', '>=': '>=', '<=': '<=', '!=': '!='}
        sql_op = op_map.get(op, '=')
        return f'json_array_length({field}) {sql_op} {n}', []
    except ValueError:
        pass

    colours = _resolve_colours(value)
    if colours is None:
        return None, []

    if colours == 'MULTI':
        thresholds = {':': '> 1', '=': '> 1', '>=': '> 1', '>': '> 2',
                      '<=': '<= 1', '<': '< 1', '!=': '<= 1'}
        expr = thresholds.get(op, '> 1')
        return f'json_array_length({field}) {expr}', []

    if colours == []:
        # colorless
        if op in (':', '=', '>=', '<='):
            return f"{field} = '[]'", []
        if op == '!=':
            return f"{field} != '[]'", []
        if op == '>':
            return f'json_array_length({field}) > 0', []
        return f"{field} = '[]'", []

    # Specific set of colours
    n = len(colours)
    contains = ' AND '.join(f"{field} LIKE ?" for _ in colours)
    c_params = [f'%"{c}"%' for c in colours]

    if op in (':', '>='):
        # at least these colours
        return f'({contains})', c_params
    if op == '=':
        # exactly these colours
        return f'({contains} AND json_array_length({field}) = {n})', c_params
    if op == '>':
        # strictly more colours than given set
        return f'({contains} AND json_array_length({field}) > {n})', c_params
    if op == '<=':
        # subset of given colours — approximate with length
        return f'json_array_length({field}) <= {n}', []
    if op == '<':
        # strict proper subset — approximate
        return f'(json_array_length({field}) < {n} AND json_array_length({field}) > 0)', []
    if op == '!=':
        return f'NOT ({contains} AND json_array_length({field}) = {n})', c_params

    # fallback
    return f'({contains})', c_params


# ─────────────────────────────────────────────────────────────
# IS: HANDLER
# ─────────────────────────────────────────────────────────────

def _is_sql(value: str, negated: bool) -> tuple[Optional[str], list, list]:
    """
    Handle is:X and not:X / -is:X queries.
    Returns (sql, params, warnings).
    """
    v   = value.lower().strip()
    neg = 'NOT ' if negated else ''

    # ── Finish options ──
    if v == 'foil':
        return f"{neg}(p.finish_options LIKE '%\"foil\"%')", [], []
    if v == 'nonfoil':
        return f"{neg}(p.finish_options LIKE '%\"nonfoil\"%')", [], []
    if v == 'etched':
        return f"{neg}(p.finish_options LIKE '%\"etched\"%')", [], []

    # ── Digital ──
    if v == 'digital':
        cond = '= 1' if not negated else '!= 1'
        return f'(c.digital {cond})', [], []

    # ── Type-line shortcuts ──
    if v == 'permanent':
        sql = (f"{neg}(LOWER(c.type_line) NOT LIKE '%instant%' "
               f"AND LOWER(c.type_line) NOT LIKE '%sorcery%')")
        return sql, [], []

    if v == 'spell':
        sql = (f"{neg}(LOWER(c.type_line) LIKE '%instant%' "
               f"OR LOWER(c.type_line) LIKE '%sorcery%')")
        return sql, [], []

    if v == 'historic':
        sql = (f"{neg}(LOWER(c.type_line) LIKE '%legendary%' "
               f"OR LOWER(c.type_line) LIKE '%artifact%' "
               f"OR LOWER(c.type_line) LIKE '%saga%')")
        return sql, [], []

    if v == 'vanilla':
        sql = f"{neg}((c.oracle_text IS NULL OR c.oracle_text = '') AND c.keywords = '[]')"
        return sql, [], []

    # ── Commander / brawl ──
    if v == 'commander':
        sql = (f"{neg}(LOWER(c.type_line) LIKE '%legendary%' "
               f"AND (LOWER(c.type_line) LIKE '%creature%' "
               f"OR c.oracle_text LIKE '%can be your commander%'))")
        return sql, [], []

    if v == 'brawler':
        sql = (f"{neg}(LOWER(c.type_line) LIKE '%legendary%' "
               f"AND (LOWER(c.type_line) LIKE '%creature%' "
               f"OR LOWER(c.type_line) LIKE '%planeswalker%'))")
        return sql, [], []

    # ── Colour shortcuts ──
    if v in ('multicolor', 'multicolour', 'multi'):
        return f"{neg}json_array_length(c.colours) > 1", [], []

    if v in ('colorless', 'colourless'):
        return f"{neg}c.colours = '[]'", [], []

    # ── Reprint / unique ──
    if v == 'reprint':
        subq = '(SELECT COUNT(DISTINCT pp.set_code) FROM printings pp WHERE pp.card_id = c.id) > 1'
        return f'{neg}({subq})', [], []

    if v == 'unique':
        subq = '(SELECT COUNT(DISTINCT pp.set_code) FROM printings pp WHERE pp.card_id = c.id) = 1'
        return f'{neg}({subq})', [], []

    # ── Land type shortcuts (oracle-text approximations) ──
    if v == 'fetchland':
        sql = (f"{neg}(LOWER(c.type_line) LIKE '%land%' "
               f"AND LOWER(c.oracle_text) LIKE '%search your library%land%')")
        return sql, [], []

    if v == 'shockland':
        sql = (f"{neg}(LOWER(c.type_line) LIKE '%land%' "
               f"AND LOWER(c.oracle_text) LIKE '%pay 2 life%')")
        return sql, [], []

    if v == 'dual':
        # Original duals: land with two basic land subtypes, no other text
        sql = (f"{neg}(LOWER(c.type_line) LIKE '%land%' "
               f"AND (LOWER(c.type_line) LIKE '%plains%' OR LOWER(c.type_line) LIKE '%island%' "
               f"OR LOWER(c.type_line) LIKE '%swamp%' OR LOWER(c.type_line) LIKE '%mountain%' "
               f"OR LOWER(c.type_line) LIKE '%forest%') "
               f"AND LOWER(c.type_line) NOT LIKE '%basic%')")
        return sql, [], []

    # ── Everything else we can't do ──
    _unsupported_is = {
        'hires', 'old', 'new', 'booster', 'promo', 'spotlight', 'reserved',
        'masterpiece', 'funny', 'split', 'flip', 'transform', 'meld', 'leveler',
        'dfc', 'mdfc', 'meldpart', 'meldresult', 'party', 'outlaw', 'modal',
        'frenchvanilla', 'bear', 'manland', 'creatureland',
        'bikeland', 'bondland', 'bounceland', 'canopyland', 'checkland',
        'fastland', 'filterland', 'gainland', 'painland', 'pathway',
        'scryland', 'surveilland', 'shadowland', 'slowland', 'storageland',
        'tangoland', 'tricycleland', 'triland',
        'partner', 'gamechanger', 'oathbreaker', 'duelcommander', 'companion',
        'colorshifted', 'alchemy', 'rebalanced', 'scryfallpreview',
        'universesbeyond', 'default', 'atypical', 'full', 'hybrid', 'phyrexian',
        'glossy', 'foiletched',
    }
    if v in _unsupported_is:
        return None, [], [f"is:{v} is not supported (no data in database)"]

    return None, [], [f"Unknown is: value '{v}'"]


# ─────────────────────────────────────────────────────────────
# NUMERIC COMPARISON HELPER
# ─────────────────────────────────────────────────────────────

def _numeric_sql(expr: str, op: str, value: str,
                 cast: str = 'REAL') -> tuple[Optional[str], list]:
    """Generate a numeric comparison. Returns (sql, params)."""
    op_map = {':': '=', '=': '=', '>': '>', '<': '<', '>=': '>=', '<=': '<=', '!=': '!='}
    sql_op = op_map.get(op)
    if not sql_op:
        return None, []
    try:
        num = float(value)
        return f'CAST({expr} AS {cast}) {sql_op} {num}', []
    except ValueError:
        return None, []


# ─────────────────────────────────────────────────────────────
# RARITY COMPARISON
# ─────────────────────────────────────────────────────────────

def _rarity_sql(op: str, value: str) -> tuple[Optional[str], list]:
    v         = value.lower()
    canonical = _RARITY_ABBREV.get(v, v)
    rank      = _RARITY_ORDER.get(canonical)
    if rank is None:
        return None, []
    if op in (':', '='):
        return 'p.rarity = ?', [canonical]
    op_map = {'>': '>', '<': '<', '>=': '>=', '<=': '<=', '!=': '!='}
    sql_op = op_map.get(op)
    if sql_op:
        return f'({_RARITY_SQL}) {sql_op} {rank}', []
    return None, []


# ─────────────────────────────────────────────────────────────
# DATE / YEAR
# ─────────────────────────────────────────────────────────────

def _date_sql(op: str, value: str,
              year_only: bool = False) -> tuple[Optional[str], list]:
    op_map = {':': '=', '=': '=', '>': '>', '<': '<', '>=': '>=', '<=': '<=', '!=': '!='}
    sql_op = op_map.get(op, '=')

    if year_only:
        if not re.match(r'^\d{4}$', value):
            return None, []
        return f"strftime('%Y', p.released_at) {sql_op} ?", [value]

    # date: can be YYYY-MM-DD or YYYY
    if re.match(r'^\d{4}-\d{2}-\d{2}$', value):
        return f'p.released_at {sql_op} ?', [value]
    if re.match(r'^\d{4}$', value):
        return f"strftime('%Y', p.released_at) {sql_op} ?", [value]
    return None, []


# ─────────────────────────────────────────────────────────────
# TERM → SQL
# ─────────────────────────────────────────────────────────────

def _term_to_sql(node: Term) -> tuple[Optional[str], list, list]:
    """
    Translate a single Term node to SQL.
    Returns (sql_fragment, params, warnings).
    sql_fragment is None for unsupported/unknown terms.
    Negation is NOT applied here — caller handles it.
    """
    key  = node.key
    op   = node.op
    val  = node.value
    warn: list[str] = []

    # Display-only — silently ignore
    if key in _DISPLAY_KEYWORDS:
        return None, [], []

    # Unsupported — warn
    if key in _UNSUPPORTED_KEYWORDS:
        warn.append(f"'{key}:' is not supported (no data in database)")
        return None, [], warn

    # ── Name ──────────────────────────────────────────────────
    if key in ('name', 'n'):
        return 'LOWER(c.name) LIKE LOWER(?)', [f'%{val}%'], []

    # ── Oracle text ───────────────────────────────────────────
    if key in ('o', 'oracle'):
        return 'LOWER(c.oracle_text) LIKE LOWER(?)', [f'%{val}%'], []

    # ── Type line ─────────────────────────────────────────────
    if key in ('t', 'type'):
        return 'LOWER(c.type_line) LIKE LOWER(?)', [f'%{val}%'], []

    # ── Colour ────────────────────────────────────────────────
    if key in ('c', 'color', 'colour'):
        sql, params = _colour_sql('c.colours', op, val)
        if sql is None:
            warn.append(f"Couldn't parse colour value: '{val}'")
        return sql, params, warn

    # ── Colour identity ───────────────────────────────────────
    if key in ('id', 'identity'):
        sql, params = _colour_sql('c.colour_identity', op, val)
        if sql is None:
            warn.append(f"Couldn't parse colour identity value: '{val}'")
        return sql, params, warn

    # ── Mana cost ─────────────────────────────────────────────
    if key in ('m', 'mana'):
        return 'c.mana_cost LIKE ?', [f'%{val}%'], []

    # ── Mana value / CMC ──────────────────────────────────────
    if key in ('mv', 'manavalue', 'cmc'):
        if val.lower() in ('even', 'odd'):
            parity = 0 if val.lower() == 'even' else 1
            return f'CAST(c.cmc AS INTEGER) % 2 = {parity}', [], []
        sql, params = _numeric_sql('c.cmc', op, val)
        if sql is None:
            warn.append(f"Couldn't parse mana value: '{val}'")
        return sql, params, warn

    # ── Power ─────────────────────────────────────────────────
    if key in ('pow', 'power'):
        if val.lower() in ('tou', 'toughness'):
            op_map = {':': '=', '=': '=', '>': '>', '<': '<',
                      '>=': '>=', '<=': '<=', '!=': '!='}
            sql_op = op_map.get(op, '=')
            return (f'CAST(c.power AS REAL) {sql_op} CAST(c.toughness AS REAL)',
                    [], [])
        sql, params = _numeric_sql('c.power', op, val)
        if sql is None:
            warn.append(f"Couldn't parse power value: '{val}'")
        return sql, params, warn

    # ── Toughness ─────────────────────────────────────────────
    if key in ('tou', 'toughness'):
        if val.lower() in ('pow', 'power'):
            op_map = {':': '=', '=': '=', '>': '>', '<': '<',
                      '>=': '>=', '<=': '<=', '!=': '!='}
            sql_op = op_map.get(op, '=')
            return (f'CAST(c.toughness AS REAL) {sql_op} CAST(c.power AS REAL)',
                    [], [])
        sql, params = _numeric_sql('c.toughness', op, val)
        if sql is None:
            warn.append(f"Couldn't parse toughness value: '{val}'")
        return sql, params, warn

    # ── Power + Toughness total ───────────────────────────────
    if key in ('pt', 'powtou'):
        expr = '(CAST(c.power AS REAL) + CAST(c.toughness AS REAL))'
        sql, params = _numeric_sql(expr, op, val)
        if sql is None:
            warn.append(f"Couldn't parse pt value: '{val}'")
        return sql, params, warn

    # ── Keywords ──────────────────────────────────────────────
    if key in ('kw', 'keyword'):
        # Stored as ["Flying", "Trample"] — title-case for matching
        kw = val.title()
        return 'c.keywords LIKE ?', [f'%"{kw}"%'], []

    # ── Format legality ───────────────────────────────────────
    if key in ('f', 'format'):
        fmt = val.lower()
        if fmt not in _VALID_FORMATS:
            warn.append(f"Unknown format: '{val}'")
            return None, [], warn
        return f"json_extract(c.legalities, '$.{fmt}') = 'legal'", [], []

    if key == 'banned':
        fmt = val.lower()
        if fmt not in _VALID_FORMATS:
            warn.append(f"Unknown format: '{val}'")
            return None, [], warn
        return f"json_extract(c.legalities, '$.{fmt}') = 'banned'", [], []

    if key == 'restricted':
        fmt = val.lower()
        if fmt not in _VALID_FORMATS:
            warn.append(f"Unknown format: '{val}'")
            return None, [], warn
        return f"json_extract(c.legalities, '$.{fmt}') = 'restricted'", [], []

    # ── Rarity ────────────────────────────────────────────────
    if key in ('r', 'rarity'):
        sql, params = _rarity_sql(op, val)
        if sql is None:
            warn.append(f"Couldn't parse rarity: '{val}'")
        return sql, params, warn

    # ── Set code ──────────────────────────────────────────────
    if key in ('s', 'e', 'set', 'edition'):
        return 'LOWER(p.set_code) = LOWER(?)', [val], []

    # ── Collector number ──────────────────────────────────────
    if key in ('cn', 'number'):
        if op in (':', '='):
            return 'p.collector_number = ?', [val], []
        sql, params = _numeric_sql('p.collector_number', op, val, 'INTEGER')
        return sql, params, warn

    # ── Artist ────────────────────────────────────────────────
    if key in ('a', 'artist'):
        return 'LOWER(p.artist) LIKE LOWER(?)', [f'%{val}%'], []

    # ── Date ──────────────────────────────────────────────────
    if key == 'date':
        sql, params = _date_sql(op, val, year_only=False)
        if sql is None:
            warn.append(f"Couldn't parse date: '{val}'")
        return sql, params, warn

    # ── Year ──────────────────────────────────────────────────
    if key == 'year':
        sql, params = _date_sql(op, val, year_only=True)
        if sql is None:
            warn.append(f"Couldn't parse year: '{val}'")
        return sql, params, warn

    # ── Custom tag ────────────────────────────────────────────
    if key == 'tag':
        sql = """EXISTS (
            SELECT 1 FROM card_tags ct
            JOIN tags tg ON tg.id = ct.tag_id
            WHERE ct.card_id = c.id AND LOWER(tg.name) = LOWER(?)
        )"""
        return sql, [val], []

    # ── is: / not: ────────────────────────────────────────────
    # Handled separately in _node_to_sql to properly pass negated state

    warn.append(f"Unknown search keyword: '{key}:'")
    return None, [], warn


# ─────────────────────────────────────────────────────────────
# AST → SQL (RECURSIVE)
# ─────────────────────────────────────────────────────────────

def _node_to_sql(node: AstNode) -> tuple[Optional[str], list, list]:
    """
    Recursively convert an AST node to a SQL fragment.
    Returns (sql, params, warnings).
    """
    warn: list[str] = []

    # ── AND ───────────────────────────────────────────────────
    if isinstance(node, AndExpr):
        if not node.children:
            return None, [], []
        parts, params = [], []
        for child in node.children:
            sql, p, w = _node_to_sql(child)
            warn.extend(w)
            if sql:
                parts.append(sql)
                params.extend(p)
        if not parts:
            return None, [], warn
        joined = ' AND '.join(parts)
        return (f'({joined})' if len(parts) > 1 else joined), params, warn

    # ── OR ────────────────────────────────────────────────────
    if isinstance(node, OrExpr):
        parts, params = [], []
        for child in node.children:
            sql, p, w = _node_to_sql(child)
            warn.extend(w)
            if sql:
                parts.append(sql)
                params.extend(p)
        if not parts:
            return None, [], warn
        joined = ' OR '.join(parts)
        return (f'({joined})' if len(parts) > 1 else joined), params, warn

    # ── Term ──────────────────────────────────────────────────
    if isinstance(node, Term):
        # is: and not: need to pass negation into the handler
        if node.key == 'is':
            sql, params, w = _is_sql(node.value, negated=node.negated)
            warn.extend(w)
            return sql, params, warn
        if node.key == 'not':
            # not:X is the same as -is:X
            sql, params, w = _is_sql(node.value, negated=not node.negated)
            warn.extend(w)
            return sql, params, warn

        sql, params, w = _term_to_sql(node)
        warn.extend(w)
        if sql is None:
            return None, [], warn
        if node.negated:
            sql = f'NOT ({sql})'
        return sql, params, warn

    # ── Bare word (→ name search) ─────────────────────────────
    if isinstance(node, BareWord):
        sql = 'LOWER(c.name) LIKE LOWER(?)'
        if node.negated:
            sql = f'NOT ({sql})'
        return sql, [f'%{node.word}%'], []

    # ── Quoted phrase (→ name OR oracle) ─────────────────────
    if isinstance(node, Phrase):
        sql = ('(LOWER(c.name) LIKE LOWER(?) '
               'OR LOWER(c.oracle_text) LIKE LOWER(?))')
        if node.negated:
            sql = f'NOT ({sql})'
        return sql, [f'%{node.phrase}%', f'%{node.phrase}%'], []

    # ── Exact name ────────────────────────────────────────────
    if isinstance(node, ExactName):
        return 'LOWER(c.name) = LOWER(?)', [node.name], []

    return None, [], warn


# ─────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────

def build_search_query(
    user_input: str,
    include_extras: bool = False,
) -> tuple[str, list, list]:
    """
    Build a complete SQL SELECT from a Scryfall-style search string.

    Args:
        user_input:    The raw search string typed by the user.
        include_extras: If False, apply Scryfall-style default exclusions
            (Vanguard, Plane but not Planeswalker, Scheme, Phenomenon, Token,
            Emblem, and cards from memorabilia sets — set_type is read from
            c.raw_scryfall_json because printings has no set_type column).

    Returns:
        (sql, params, warnings)
        sql      — complete SELECT query, safe to pass to pandas.read_sql_query
        params   — positional parameters matching the ? placeholders in sql
        warnings — list of human-readable strings about unsupported syntax
    """
    base = """
        SELECT c.id, c.name, p.image_url
        FROM cards c
        LEFT JOIN printings p ON p.card_id = c.id
    """

    conditions: list[str] = []
    params:     list      = []
    warnings:   list[str] = []

    # ── Scryfall default filters (when not including extras) ──
    if not include_extras:
        conditions.extend(
            [
                "LOWER(c.type_line) NOT LIKE '%vanguard%'",
                "NOT (LOWER(c.type_line) LIKE '%plane%' AND LOWER(c.type_line) NOT LIKE '%planeswalker%')",
                "LOWER(c.type_line) NOT LIKE '%scheme%'",
                "LOWER(c.type_line) NOT LIKE '%phenomenon%'",
                "LOWER(c.type_line) NOT LIKE '%token%'",
                "LOWER(c.type_line) NOT LIKE '%emblem%'",
                # tak.db has no set_type on printings/cards; Scryfall card JSON includes set_type
                "NOT (LOWER(IFNULL(json_extract(c.raw_scryfall_json, '$.set_type'), '')) = 'memorabilia')",
            ]
        )

    # ── User query ────────────────────────────────────────────
    if user_input and user_input.strip():
        ast = _parse(user_input)
        sql_frag, q_params, q_warns = _node_to_sql(ast)
        warnings.extend(q_warns)
        if sql_frag:
            conditions.append(sql_frag)
            params.extend(q_params)

    full_query = base
    if conditions:
        full_query += 'WHERE ' + '\n  AND '.join(conditions) + '\n'
    full_query += 'GROUP BY c.id'

    return full_query, params, warnings


# ─────────────────────────────────────────────────────────────
# QUICK SELF-TEST  (python search.py)
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    tests = [
        # Basic
        'lightning',
        '"draw a card"',
        '!Lightning Bolt',
        # Keywords
        't:creature o:"draw a card"',
        't:goblin -t:creature',
        'kw:flying c:u mv<=3',
        # Colour
        'c:rg t:creature',
        'c=2 t:instant',
        'id:esper t:instant',
        'c:m -c:blue',
        # Numeric
        'pow>=8',
        'pow>tou c:w',
        'mv:even t:creature c:g',
        # Rarity / set / artist
        'r>=rare e:war',
        'r:common t:artifact',
        'a:avon t:land',
        # Format
        'f:commander t:creature c:g',
        'banned:legacy',
        # Date
        'year>=2020 r:mythic',
        'date>2015-08-18',
        # is:
        'is:commander -t:human',
        'is:fetchland',
        'is:foil e:c16',
        'is:vanilla t:creature',
        # OR and nesting
        '(t:goblin or t:elf) r:rare',
        't:creature (c:r or c:g) mv<=3',
        # Negation
        '-fire c:r t:instant',
        '-is:digital f:modern',
        # Tag
        'tag:ramp c:g',
        # Unsupported (should warn, not crash)
        'ft:mishra usd>=5',
    ]

    for q in tests:
        sql, params, warns = build_search_query(q)
        print(f'\nQUERY:  {q}')
        if warns:
            print(f'WARNS:  {warns}')
        # Print just the WHERE clause for readability
        where_start = sql.find('WHERE')
        if where_start != -1:
            print(f'WHERE:  {sql[where_start:].strip()}')
        print(f'PARAMS: {params}')
