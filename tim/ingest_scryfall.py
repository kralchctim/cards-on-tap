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


def insert_data(cards_json):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Clearing existing data...")
    cursor.execute("DELETE FROM printings;")
    cursor.execute("DELETE FROM cards;")

    conn.commit()

    print("Inserting cards...")

    oracle_id_to_card_id = {}

    # First pass: cards (unique by oracle_id)
    for card in tqdm(cards_json):
        oracle_id = card.get("oracle_id")

        if oracle_id in oracle_id_to_card_id:
            continue

        cursor.execute("""
            INSERT INTO cards (
                oracle_id, name, mana_cost, type_line, oracle_text,
                power, toughness, colours, colour_identity, cmc,
                legalities, keywords, raw_scryfall_json
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
            json.dumps(card)
        ))

        card_id = cursor.lastrowid
        oracle_id_to_card_id[oracle_id] = card_id

    conn.commit()

    print("Inserting printings...")

    # Second pass: printings
    for card in tqdm(cards_json):
        oracle_id = card.get("oracle_id")
        card_id = oracle_id_to_card_id.get(oracle_id)

        if not card_id:
            continue

        cursor.execute("""
            INSERT OR IGNORE INTO printings (
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
            (card.get("image_uris") or {}).get("normal"),
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
