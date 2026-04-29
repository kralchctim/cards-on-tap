def choose_from_matches(
    label: str,
    top_matches: list[tuple[str, float]]
) -> str:
    """
    Let the user choose from matched set codes / collector numbers,
    or type their own manual correction.
    """
    if not top_matches:
        return input(f"No {label} matches found. Type the {label} manually: ").strip()

    print(f"\nTop {label} matches:")
    for i, (value, score) in enumerate(top_matches, start=1):
        print(f"{i}. {value} ({score:.1f})")

    print(f"Press Enter to accept option 1, type 2 or 3 to choose another option,")
    print(f"or type the {label} manually.")

    user_input = input(f"Your {label} choice: ").strip()

    if user_input == "":
        return top_matches[0][0]

    if user_input in {"1", "2", "3"}:
        index = int(user_input) - 1
        if index < len(top_matches):
            return top_matches[index][0]

    return user_input.strip()


def choose_set_code(set_codes: list[str]) -> str:
    """
    Manual fallback if needed.
    """
    if not set_codes:
        return ""

    if len(set_codes) == 1:
        print(f"Only one set available: {set_codes[0]}")
        return set_codes[0]

    print("\nPossible set codes:")
    for i, set_code in enumerate(set_codes, start=1):
        print(f"{i}. {set_code}")

    while True:
        user_input = input("Choose a set code by number or type it manually: ").strip()

        if user_input.isdigit():
            index = int(user_input) - 1
            if 0 <= index < len(set_codes):
                return set_codes[index]

        if user_input:
            return user_input.lower()


def choose_collector_number(collector_numbers: list[str]) -> str:
    """
    Manual fallback if needed.
    """
    if not collector_numbers:
        return ""

    if len(collector_numbers) == 1:
        print(f"Only one collector number available: {collector_numbers[0]}")
        return collector_numbers[0]

    print("\nPossible collector numbers:")
    for i, number in enumerate(collector_numbers, start=1):
        print(f"{i}. {number}")

    while True:
        user_input = input("Choose a collector number by number or type it manually: ").strip()

        if user_input.isdigit():
            index = int(user_input) - 1
            if 0 <= index < len(collector_numbers):
                return collector_numbers[index]

        if user_input:
            return user_input
