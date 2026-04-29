from app.modules.card_name_loader import load_card_names
from app.modules.scryfall_lookup import search_cards_by_filter


def get_candidate_names() -> list[str]:
    """
    Ask once whether to use the full card-name list or a filtered Scryfall candidate list.
    Returns a list of candidate card names for this run.
    """
    print("\nCandidate set options:")
    print("1. Use the full Scryfall card-name list")
    print("2. Use a filtered Scryfall candidate list")

    choice = input("Choose 1 or 2 (press Enter for 1): ").strip()

    if choice in {"", "1"}:
        names = load_card_names()
        print(f"Using full candidate list with {len(names)} names.")
        return names

    if choice == "2":
        filter_query = input("Enter Scryfall filter text: ").strip()

        if not filter_query:
            print("No filter entered. Falling back to full candidate list.")
            names = load_card_names()
            print(f"Using full candidate list with {len(names)} names.")
            return names

        try:
            cards = search_cards_by_filter(filter_query)
            names = sorted({card.get("name", "").strip() for card in cards if card.get("name", "").strip()})

            if not names:
                print("No names returned by filter. Falling back to full candidate list.")
                names = load_card_names()
                print(f"Using full candidate list with {len(names)} names.")
                return names

            print(f"Using filtered candidate list with {len(names)} names.")
            return names

        except Exception as e:
            print(f"Filtering failed: {e}")
            print("Falling back to full candidate list.")
            names = load_card_names()
            print(f"Using full candidate list with {len(names)} names.")
            return names

    print("Invalid choice. Falling back to full candidate list.")
    names = load_card_names()
    print(f"Using full candidate list with {len(names)} names.")
    return names
