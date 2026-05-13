import sqlite3
from pathlib import Path

def _resolve_reference_db_path() -> str:
    """
    Resolve the reference database path.

    `tim/` is the source of truth for `tak.db`; `steve/` should always read
    from that file regardless of the current working directory.
    """
    this_file = Path(__file__).resolve()
    for parent in this_file.parents:
        candidate = parent / "tim" / "tak.db"
        if candidate.is_file():
            return str(candidate)

    # If we get here, the repo layout isn't what we expect.
    raise FileNotFoundError(
        "Could not locate the reference database at 'tim/tak.db' "
        f"(searched relative to: {this_file})."
    )


DB_PATH = _resolve_reference_db_path()


def _row_to_card(row: tuple) -> dict:
    """
    Convert a (cards, printings) joined row into the dict shape that
    the rest of the app expects (matching former Scryfall fields).
    """
    (
        name,
        set_code,
        collector_number,
        mana_cost,
        type_line,
        oracle_text,
    ) = row

    # `get_best_card()` uses a LEFT JOIN, so printing columns can be NULL.
    # Normalize NULLs to empty strings so downstream string formatting stays safe.
    def nz(value) -> str:
        return "" if value is None else str(value)

    return {
        "name": nz(name),
        "set": nz(set_code),
        "collector_number": nz(collector_number),
        "mana_cost": nz(mana_cost),
        "type_line": nz(type_line),
        "oracle_text": nz(oracle_text),
    }


def get_best_card(card_name: str, extra_query: str = "") -> dict | None:
    """
    Look up a card in tak.db by name and return a single "best" printing.

    Strategy:
    - Match card name case-insensitively in the cards table
    - Prefer the most recently released printing (released_at DESC)
    """
    card_name = card_name.strip()

    if not card_name:
        return None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            c.name,
            p.set_code,
            p.collector_number,
            c.mana_cost,
            c.type_line,
            c.oracle_text
        FROM cards c
        LEFT JOIN printings p ON p.card_id = c.id
        WHERE LOWER(c.name) = LOWER(?)
        ORDER BY p.released_at DESC
        LIMIT 1
        """,
        (card_name,),
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return _row_to_card(row)


def search_cards_by_filter(filter_query: str) -> list[dict]:
    """
    Approximate the old Scryfall `search_cards_by_filter` using tak.db.

    For now this treats `filter_query` as free text and matches it against
    card name or oracle_text (case-insensitive). It returns a list of
    card-like dicts (only the `name` field is relied on by callers).
    """
    filter_query = filter_query.strip()

    if not filter_query:
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    like = f"%{filter_query}%"

    cursor.execute(
        """
        SELECT DISTINCT c.name
        FROM cards c
        WHERE LOWER(c.name) LIKE LOWER(?)
           OR LOWER(c.oracle_text) LIKE LOWER(?)
        """,
        (like, like),
    )

    rows = cursor.fetchall()
    conn.close()

    return [{"name": row[0]} for row in rows if row and row[0]]


def print_card_summary(card: dict) -> None:
    """
    Print a friendly summary of a card dict coming from tak.db.
    """
    if not card:
        print("\nNo card found.")
        return

    name = card.get("name", "Unknown")
    set_code = (card.get("set") or "").upper()
    collector_number = card.get("collector_number", "") or ""
    mana_cost = card.get("mana_cost", "") or ""
    type_line = card.get("type_line", "") or ""
    oracle_text = card.get("oracle_text", "") or ""

    print("\n=== Best Match ===")
    print(f"Name: {name}")
    print(f"Mana Cost: {mana_cost}")
    print(f"Type: {type_line}")
    print(f"Set: {set_code} #{collector_number}")
    print(f"Oracle Text: {oracle_text}")


def get_card_by_set_and_number(set_code: str, collector_number: str) -> dict | None:
    """
    Fetch a specific printing from tak.db by set code and collector number.
    """
    set_code = set_code.strip().lower()
    collector_number = collector_number.strip()

    if not set_code or not collector_number:
        return None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            c.name,
            p.set_code,
            p.collector_number,
            c.mana_cost,
            c.type_line,
            c.oracle_text
        FROM printings p
        JOIN cards c ON c.id = p.card_id
        WHERE LOWER(p.set_code) = LOWER(?)
          AND p.collector_number = ?
        ORDER BY p.released_at DESC
        LIMIT 1
        """,
        (set_code, collector_number),
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return _row_to_card(row)
