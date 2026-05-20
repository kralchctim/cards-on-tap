"""
main.py — TAK API backend
"""

from dotenv import load_dotenv
load_dotenv()

import sqlite3
from fastapi import FastAPI, HTTPException, Query, Body, Depends
from fastapi.middleware.cors import CORSMiddleware

from search import build_search_query
from auth import get_current_user

DB_PATH = "tak.db"

app = FastAPI(title="TAK API", version="0.1.0")

# ─────────────────────────────────────────────────────────────
# CORS — allows the React dev server (port 5173) to call us.
# In production you'll swap localhost for your deployed URL.
# ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # fallback
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# DB HELPER
# ─────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # rows behave like dicts
    return conn


# ─────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────
# CARD SEARCH
# ─────────────────────────────────────────────────────────────

@app.get("/cards/search")
def search_cards(
    q:               str  = Query(default="", description="Scryfall-style search query"),
    include_extras:  bool = Query(
        default=False,
        description="Include extras (Vanguard, Plane, Scheme, Phenomenon, Tokens, Emblems, Memorabilia sets)",
    ),
    include_arena:   bool = Query(
        default=False,
        description="Include MTG Arena/digital-only cards",
    ),
    page:            int  = Query(default=0, ge=0),
    page_size:       int  = Query(default=60, ge=1, le=200),
):
    """
    Search cards using Scryfall-style syntax.
    Returns a paginated list of cards with their best printing image.
    """
    sql, params, warnings = build_search_query(
        q,
        include_extras=include_extras,
        include_arena=include_arena,
    )

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    finally:
        conn.close()

    total     = len(rows)
    start     = page * page_size
    paginated = rows[start : start + page_size]

    return {
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "warnings":  warnings,
        "cards":     [dict(r) for r in paginated],
    }


# ─────────────────────────────────────────────────────────────
# CARD DETAIL
# ─────────────────────────────────────────────────────────────

@app.get("/cards/{card_id}")
def get_card(card_id: int):
    """Full card details including tags."""
    conn = get_db()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Card not found")

        card = dict(row)

        # Tags
        cursor.execute("""
            SELECT t.id, t.name, t.category, t.description
            FROM tags t
            JOIN card_tags ct ON t.id = ct.tag_id
            WHERE ct.card_id = ?
            ORDER BY t.name
        """, (card_id,))
        card["tags"] = [dict(r) for r in cursor.fetchall()]

    finally:
        conn.close()

    return card


# ─────────────────────────────────────────────────────────────
# PRINTINGS FOR A CARD
# ─────────────────────────────────────────────────────────────

@app.get("/cards/{card_id}/printings")
def get_printings(card_id: int):
    """All printings of a card, newest first."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, scryfall_id, set_code, collector_number,
                   rarity, artist, image_url, finish_options, released_at
            FROM printings
            WHERE card_id = ?
            ORDER BY released_at DESC
        """, (card_id,))
        rows = cursor.fetchall()
    finally:
        conn.close()

    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────
# TAGS
# ─────────────────────────────────────────────────────────────

@app.get("/tags")
def list_tags():
    """All tags, alphabetically."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, category, description, source
            FROM tags
            ORDER BY name
        """)
        rows = cursor.fetchall()
    finally:
        conn.close()

    return [dict(r) for r in rows]


@app.get("/tags/{tag_id}/cards")
def get_tag_cards(tag_id: int):
    """All cards with a given tag."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.name
            FROM cards c
            JOIN card_tags ct ON ct.card_id = c.id
            WHERE ct.tag_id = ?
            ORDER BY c.name
        """, (tag_id,))
        rows = cursor.fetchall()
    finally:
        conn.close()

    return [dict(r) for r in rows]

# ─────────────────────────────────────────────────────────────
# TAG MUTATIONS
# ─────────────────────────────────────────────────────────────

@app.post("/cards/{card_id}/tags")
def add_tag_to_card(
    card_id: int,
    name:        str  = Body(...),
    description: str  = Body(default=""),
):
    """
    Find or create a tag by name, then attach it to the card.
    Returns the tag that was added.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()

        # Card must exist
        cursor.execute("SELECT id FROM cards WHERE id = ?", (card_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Card not found")

        # Find or create the tag
        cursor.execute("SELECT id FROM tags WHERE LOWER(name) = LOWER(?)", (name,))
        row = cursor.fetchone()
        if row:
            tag_id = row["id"]
        else:
            cursor.execute(
                "INSERT INTO tags (name, description, category, source) VALUES (?, ?, ?, ?)",
                (name, description, "manual", "manual")
            )
            tag_id = cursor.lastrowid

        # Attach (ignore if already attached)
        cursor.execute("""
            INSERT OR IGNORE INTO card_tags 
            (card_id, tag_id, confidence_score, source, reviewed_status)
            VALUES (?, ?, 1.0, 'manual', 'manual')
        """, (card_id, tag_id))

        conn.commit()

        cursor.execute("SELECT * FROM tags WHERE id = ?", (tag_id,))
        return dict(cursor.fetchone())

    finally:
        conn.close()


@app.delete("/cards/{card_id}/tags/{tag_id}")
def remove_tag_from_card(card_id: int, tag_id: int):
    """Remove a tag from a card."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM card_tags WHERE card_id = ? AND tag_id = ?",
            (card_id, tag_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Tag not on this card")
        return {"ok": True}
    finally:
        conn.close()
