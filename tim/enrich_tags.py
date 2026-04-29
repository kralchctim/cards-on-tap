import requests
import sqlite3
from tqdm import tqdm

DB_PATH = "tak.db"

SCRYFALL_SEARCH_URL = "https://api.scryfall.com/cards/search"

def get_all_cards_for_query(query):
    cards = []
    url = SCRYFALL_SEARCH_URL
    params = {"q": query}

    while url:
        response = requests.get(url, params=params if url == SCRYFALL_SEARCH_URL else None)
        data = response.json()

        cards.extend(data["data"])

        if data.get("has_more"):
            url = data["next_page"]
        else:
            url = None

    return cards


def ensure_tag_exists(cursor, tag_name):
    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
    result = cursor.fetchone()

    if result:
        return result[0]

    cursor.execute(
        "INSERT INTO tags (name, category, description, source) VALUES (?, ?, ?, ?)",
        (tag_name, "gameplay", None, "scryfall_otag")
    )

    return cursor.lastrowid


def enrich_tag(query, tag_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"Fetching cards for query: {query}")
    cards = get_all_cards_for_query(query)

    print(f"Found {len(cards)} results from Scryfall")

    tag_id = ensure_tag_exists(cursor, tag_name)

    added = 0

    for card in tqdm(cards):
        oracle_id = card.get("oracle_id")

        # find matching card in your DB
        cursor.execute("SELECT id FROM cards WHERE oracle_id = ?", (oracle_id,))
        result = cursor.fetchone()

        if not result:
            continue

        card_id = result[0]

        # insert tag if not already present
        cursor.execute("""
            SELECT 1 FROM card_tags 
            WHERE card_id = ? AND tag_id = ?
        """, (card_id, tag_id))

        if cursor.fetchone():
            continue

        cursor.execute("""
            INSERT INTO card_tags (card_id, tag_id, confidence_score, source, reviewed_status)
            VALUES (?, ?, ?, ?, ?)
        """, (card_id, tag_id, 1.0, "scryfall_otag", "auto"))

        added += 1

    conn.commit()
    conn.close()

    print(f"Added tag '{tag_name}' to {added} cards")


if __name__ == "__main__":
    TAGS = [
        ("otag:card-advantage", "Card Advantage"),
        ("otag:ramp", "Ramp"),
        ("otag:spot-removal", "Targeted Disruption"),
        ("otag:counterspell", "Targeted Disruption"),
        ("otag:sweeper", "Mass Disruption"),
        ("otag:multi-removal", "Mass Disruption"),
    ]

    for query, tag_name in TAGS:
        enrich_tag(query, tag_name)
