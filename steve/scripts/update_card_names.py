import requests
from pathlib import Path


SCRYFALL_CARD_NAMES_URL = "https://api.scryfall.com/catalog/card-names"
OUTPUT_FILE = Path("data/card_names.txt")


def fetch_card_names() -> list[str]:
    response = requests.get(SCRYFALL_CARD_NAMES_URL, timeout=30)
    response.raise_for_status()

    data = response.json()
    return data.get("data", [])


def save_card_names(card_names: list[str], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as file:
        for name in card_names:
            file.write(f"{name}\n")


def main():
    print("Fetching card names from Scryfall...")

    card_names = fetch_card_names()
    print(f"Fetched {len(card_names)} card names.")

    save_card_names(card_names, OUTPUT_FILE)
    print(f"Saved card names to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
