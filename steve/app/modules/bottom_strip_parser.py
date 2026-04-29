import re


VALID_RARITIES = {"C", "U", "R", "M"}


def parse_bottom_strip_text(text: str) -> dict:
    """
    Parse OCR text from the bottom-left strip of a modern MTG card.

    Returns a dictionary with best-guess fields:
    - collector_number
    - set_code
    - rarity
    - language
    """
    original_text = text

    # Clean obvious OCR noise a bit
    cleaned = text.upper()
    cleaned = cleaned.replace("\n", " ").replace("\r", " ")
    cleaned = re.sub(r"[^A-Z0-9/\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    tokens = cleaned.split()

    collector_number = ""
    set_code = ""
    rarity = ""
    language = ""

    # Language: for your cards, EN
    if "EN" in tokens:
        language = "EN"

    # Rarity: single token C/U/R/M
    for token in tokens:
        if token in VALID_RARITIES:
            rarity = token
            break

    # Set code:
    # - exactly 3 alphanumeric characters
    # - not EN
    # - not just a rarity letter
    # - must contain at least one letter (so "832" is not a set code)
    set_code_candidates = []
    for token in tokens:
        if (
            len(token) == 3
            and token.isalnum()
            and token != "EN"
            and token not in VALID_RARITIES
            and any(ch.isalpha() for ch in token)
        ):
            set_code_candidates.append(token)

    if set_code_candidates:
        set_code = set_code_candidates[0]

    # Collector number:
    # - if token looks like 123 or 0059, use it
    # - if token looks like 100/500, use 100
    for token in tokens:
        if re.fullmatch(r"\d+", token):
            collector_number = token
            break

        match = re.fullmatch(r"(\d+)/\d+", token)
        if match:
            collector_number = match.group(1)
            break

    return {
        "original_text": original_text,
        "cleaned_text": cleaned,
        "collector_number": collector_number,
        "set_code": set_code,
        "rarity": rarity,
        "language": language,
    }
