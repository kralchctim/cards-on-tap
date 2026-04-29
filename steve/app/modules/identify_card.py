from pathlib import Path


def get_image_paths(images_dir: str = "input/images") -> list[Path]:
    """
    Return all image files in the input/images folder.
    """
    folder = Path(images_dir)

    if not folder.exists():
        raise FileNotFoundError(f"Image folder not found: {folder}")

    image_paths = []
    for pattern in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        image_paths.extend(folder.glob(pattern))

    image_paths = sorted(image_paths)

    if not image_paths:
        raise FileNotFoundError(f"No image files found in: {folder}")

    return image_paths


def choose_card_name(top_matches: list[tuple[str, float]]) -> str:
    """
    Let the user choose from fuzzy-matched card names or type their own correction.
    """
    if not top_matches:
        return input("No matches found. Type the card name manually: ").strip()

    top_score = top_matches[0][1]

    print("\nTop matches:")
    for i, (name, score) in enumerate(top_matches, start=1):
        print(f"{i}. {name} ({score:.1f})")

    if top_score < 80:
        print("\nWarning: these matches look weak. The real card may not be in the current candidate set.")
        return input("Type the card name manually, or choose 1/2/3 anyway: ").strip()

    print("Press Enter to accept option 1, type 2 or 3 to choose another option,")
    print("or type your own card name manually.")

    user_input = input("Your choice: ").strip()

    if user_input == "":
        return top_matches[0][0]

    if user_input in {"1", "2", "3"}:
        index = int(user_input) - 1
        if index < len(top_matches):
            return top_matches[index][0]

    return user_input
