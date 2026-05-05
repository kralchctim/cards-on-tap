import requests
import sqlite3
import json
from tqdm import tqdm

DB_PATH = "tak.db"

def get_bulk_data_url():
    url = "https://api.scryfall.com/bulk-data"
    response = requests.get(url)
    data = response.json()

    for item in data["data"]:
        if item["type"] == "default_cards":
            return item["download_uri"]

    raise Exception("Default cards bulk data not found")


def download_bulk_data(url):
    print("Downloading bulk data...")
    response = requests.get(url)
    return response.json()


# -----------------------
# NEW: IMAGE EXTRACTION
# -----------------------
def extract_image_urls(card):
    # Single-face
    if "image_uris" in card:
        return card["image_uris"].get("normal")

    # Multi-face
    if "card_faces" in card:
        urls = []
        for face in card["card_faces"]:
            if "image_uris" in face:
                urls.append(face["image_uris"]["normal"])
        return "|".join(urls)

    return None


def insert_data(cards_json):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Upserting cards...")

    oracle_id_to_card_id = {}

    # -----------------------
    # CARDS (UPSERT)
    # -----------------------
    for card in tqdm(cards_json):
        oracle_id = card.get("oracle_id")
        digital = 1 if card.get("digital") else 0

        # check if exists
        cursor.execute("SELECT id FROM cards WHERE oracle_id = ?", (oracle_id,))
        existing = cursor.fetchone()

        if existing:
            card_id = existing[0]

            # UPDATE existing
            cursor.execute("""
                UPDATE cards SET
                    name = ?,
                    mana_cost = ?,
                    type_line = ?,
                    oracle_text = ?,
                    power = ?,
                    toughness = ?,
                    colours = ?,
                    colour_identity = ?,
                    cmc = ?,
                    legalities = ?,
                    keywords = ?,
                    raw_scryfall_json = ?
                    digital = ?
                WHERE id = ?
            """, (
                card.get("name"),
                card.get("mana_cost"),
                card.get("type_line"),
                card.get("oracle_text"),
                card.get("power"),
                card.get("toughness"),
                json.dumps(card.get("colors")),
                json.dumps(card.get("color_identity")),
                card.get("cmc"),
                json.dumps(card.get("legalities")),
                json.dumps(card.get("keywords")),
                json.dumps(card),
                digital,
                card_id
            ))

        else:
            # INSERT new
            cursor.execute("""
                INSERT INTO cards (
                    oracle_id, name, mana_cost, type_line, oracle_text,
                    power, toughness, colours, colour_identity, cmc,
                    legalities, keywords, raw_scryfall_json, digital
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                oracle_id,
                card.get("name"),
                card.get("mana_cost"),
                card.get("type_line"),
                card.get("oracle_text"),
                card.get("power"),
                card.get("toughness"),
                json.dumps(card.get("colors")),
                json.dumps(card.get("color_identity")),
                card.get("cmc"),
                json.dumps(card.get("legalities")),
                json.dumps(card.get("keywords")),
                json.dumps(card),
                digital
            ))

            card_id = cursor.lastrowid

        oracle_id_to_card_id[oracle_id] = card_id

    conn.commit()

    print("Refreshing printings...")

    # Safe to clear printings (no tags depend on this)
    cursor.execute("DELETE FROM printings;")
    conn.commit()

    # -----------------------
    # PRINTINGS
    # -----------------------
    for card in tqdm(cards_json):
        oracle_id = card.get("oracle_id")
        card_id = oracle_id_to_card_id.get(oracle_id)

        if not card_id:
            continue

        image_urls = extract_image_urls(card)

        cursor.execute("""
            INSERT INTO printings (
                card_id, scryfall_id, set_code, collector_number,
                rarity, artist, image_url, finish_options, released_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            card_id,
            card.get("id"),
            card.get("set"),
            card.get("collector_number"),
            card.get("rarity"),
            card.get("artist"),
            image_urls,
            json.dumps(card.get("finishes")),
            card.get("released_at")
        ))

    conn.commit()
    conn.close()

    print("Done.")


def main():
    url = get_bulk_data_url()
    data = download_bulk_data(url)
    insert_data(data)


if __name__ == "__main__":
    main()
