from pathlib import Path


def load_card_names(file_path: str = "data/card_names.txt") -> list[str]:
    """
    Load card names from a text file, one card name per line.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Card name file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        names = [line.strip() for line in file if line.strip()]

    return names
