import requests


SCRYFALL_SEARCH_URL = "https://api.scryfall.com/cards/search"


def run_search(query: str) -> list[dict]:
    """
    Run a raw Scryfall search query and return card results.
    If Scryfall returns no cards, return an empty list.
    """
    params = {"q": query}
    response = requests.get(SCRYFALL_SEARCH_URL, params=params, timeout=30)

    if response.status_code == 404:
        return []

    response.raise_for_status()
    data = response.json()

    return data.get("data", [])


def search_cards(card_name: str, extra_query: str = "") -> list[dict]:
    """
    Search Scryfall for a card name, with optional extra filter text.

    Strategy:
    1. Try exact name match first
    2. If that fails, try a looser search
    """
    card_name = card_name.strip()
    extra_query = extra_query.strip()

    if not card_name:
        raise ValueError("card_name cannot be empty.")

    exact_query = f'!"{card_name}"'
    if extra_query:
        exact_query = f"{exact_query} {extra_query}"

    exact_results = run_search(exact_query)
    if exact_results:
        return exact_results

    loose_query = card_name
    if extra_query:
        loose_query = f"{loose_query} {extra_query}"

    return run_search(loose_query)


def search_cards_by_filter(filter_query: str) -> list[dict]:
    """
    Search Scryfall using filter text only, fetching all pages.
    """
    filter_query = filter_query.strip()

    if not filter_query:
        return []

    all_cards = []
    next_url = SCRYFALL_SEARCH_URL
    params = {"q": filter_query}

    while next_url:
        response = requests.get(next_url, params=params, timeout=30)

        if response.status_code == 404:
            return []

        response.raise_for_status()
        data = response.json()

        all_cards.extend(data.get("data", []))

        if data.get("has_more") and data.get("next_page"):
            next_url = data["next_page"]
            params = None  # next_page already includes the query
        else:
            next_url = None

    return all_cards


def get_best_card(card_name: str, extra_query: str = "") -> dict | None:
    """
    Return the first result from Scryfall, or None if nothing is found.
    """
    try:
        cards = search_cards(card_name, extra_query)
    except Exception:
        return None

    if not cards:
        return None

    return cards[0]


def print_card_summary(card: dict) -> None:
    """
    Print a friendly summary of a Scryfall card result.
    """
    if not card:
        print("\nNo card found.")
        return

    name = card.get("name", "Unknown")
    set_code = card.get("set", "").upper()
    collector_number = card.get("collector_number", "")
    mana_cost = card.get("mana_cost", "")
    type_line = card.get("type_line", "")
    oracle_text = card.get("oracle_text", "")

    print("\n=== Best Match ===")
    print(f"Name: {name}")
    print(f"Mana Cost: {mana_cost}")
    print(f"Type: {type_line}")
    print(f"Set: {set_code} #{collector_number}")
    print(f"Oracle Text: {oracle_text}")


def get_card_by_set_and_number(set_code: str, collector_number: str) -> dict | None:
    """
    Fetch a specific printing from Scryfall by set code and collector number.
    """
    set_code = set_code.strip().lower()
    collector_number = collector_number.strip()

    if not set_code or not collector_number:
        return None

    url = f"https://api.scryfall.com/cards/{set_code}/{collector_number}"

    response = requests.get(url, timeout=30)

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json()
