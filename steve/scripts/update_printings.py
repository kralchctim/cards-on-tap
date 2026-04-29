import json
import requests
from pathlib import Path


BULK_DATA_URL = "https://api.scryfall.com/bulk-data/default_cards"
RAW_DOWNLOAD_PATH = Path("data/default_cards.json")
OUTPUT_PATH = Path("data/printings.jsonl")


def fetch_bulk_metadata() -> dict:
    response = requests.get(BULK_DATA_URL, timeout=30)
    response.raise_for_status()
    return response.json()


def download_bulk_file(download_uri: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(download_uri, stream=True, timeout=120) as response:
        response.raise_for_status()

        with output_path.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)


def build_printings_file(raw_json_path: Path, output_path: Path) -> int:
    with raw_json_path.open("r", encoding="utf-8") as file:
        cards = json.load(file)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with output_path.open("w", encoding="utf-8") as out_file:
        for card in cards:
            name = card.get("name")
            set_code = card.get("set")
            collector_number = card.get("collector_number")

            if not name or not set_code or not collector_number:
                continue

            slim_record = {
                "name": name,
                "set": set_code,
                "collector_number": collector_number,
            }

            out_file.write(json.dumps(slim_record, ensure_ascii=False) + "\n")
            count += 1

    return count


def main():
    print("Fetching bulk metadata from Scryfall...")
    metadata = fetch_bulk_metadata()

    download_uri = metadata.get("download_uri")
    if not download_uri:
        raise RuntimeError("Could not find download_uri in Scryfall bulk metadata.")

    print("Downloading default_cards bulk file...")
    download_bulk_file(download_uri, RAW_DOWNLOAD_PATH)
    print(f"Saved raw bulk file to: {RAW_DOWNLOAD_PATH}")

    print("Building slim printings file...")
    count = build_printings_file(RAW_DOWNLOAD_PATH, OUTPUT_PATH)
    print(f"Saved {count} printings to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
