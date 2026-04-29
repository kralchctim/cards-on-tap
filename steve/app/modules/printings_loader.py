import json
from pathlib import Path


PRINTINGS_FILE = Path("data/printings.jsonl")


def load_printings() -> list[dict]:
    """
    Load all printings from the local JSONL file.
    """
    if not PRINTINGS_FILE.exists():
        raise FileNotFoundError(f"Printings file not found: {PRINTINGS_FILE}")

    printings = []

    with PRINTINGS_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            record = json.loads(line)
            printings.append(record)

    return printings


def get_printings_for_name(card_name: str, printings: list[dict]) -> list[dict]:
    """
    Return all printings for a given card name.
    """
    return [p for p in printings if p.get("name") == card_name]


def get_sets_for_name(card_name: str, printings: list[dict]) -> list[str]:
    """
    Return sorted unique set codes for a given card name.
    """
    sets = {p.get("set") for p in printings if p.get("name") == card_name}
    return sorted(s for s in sets if s)


def get_collector_numbers_for_name_and_set(card_name: str, set_code: str, printings: list[dict]) -> list[str]:
    """
    Return sorted unique collector numbers for a given card name in a given set.
    """
    numbers = {
        p.get("collector_number")
        for p in printings
        if p.get("name") == card_name and p.get("set") == set_code
    }
    return sorted(n for n in numbers if n)

def normalize_collector_number(number: str) -> str:
    """
    Normalize collector numbers for matching.
    For now, if it's purely numeric, strip leading zeros.
    Otherwise leave it alone.
    """
    number = str(number).strip()

    if number.isdigit():
        return str(int(number))

    return number


def get_normalized_collector_numbers_for_name_and_set(
    card_name: str,
    set_code: str,
    printings: list[dict]
) -> list[str]:
    """
    Return sorted unique normalized collector numbers for a given card name in a given set.
    """
    raw_numbers = get_collector_numbers_for_name_and_set(card_name, set_code, printings)
    normalized = {normalize_collector_number(n) for n in raw_numbers if n}
    return sorted(normalized)
