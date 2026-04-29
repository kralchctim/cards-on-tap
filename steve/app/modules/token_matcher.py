from rapidfuzz import process, fuzz


def get_top_token_matches(
    guess: str,
    candidate_tokens: list[str],
    limit: int = 3,
    normalize_case: bool = True
) -> list[tuple[str, float]]:
    """
    Return the top fuzzy matches for a short token (like set code or collector number)
    against a list of valid candidates.

    If normalize_case is True, compare everything in lowercase but return the original values.
    """
    guess = guess.strip()
    if not guess or not candidate_tokens:
        return []

    if normalize_case:
        normalized_guess = guess.lower()
        normalized_choices = {token.lower(): token for token in candidate_tokens}

        matches = process.extract(
            query=normalized_guess,
            choices=list(normalized_choices.keys()),
            scorer=fuzz.WRatio,
            limit=limit,
        )

        results = []
        for matched_normalized, score, _ in matches:
            original_value = normalized_choices[matched_normalized]
            results.append((original_value, score))

        return results

    matches = process.extract(
        query=guess,
        choices=candidate_tokens,
        scorer=fuzz.WRatio,
        limit=limit,
    )

    results = []
    for match_value, score, _ in matches:
        results.append((match_value, score))

    return results
