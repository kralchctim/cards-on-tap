from rapidfuzz import process, fuzz


def get_top_name_matches(
    ocr_text: str,
    candidate_names: list[str],
    limit: int = 3
) -> list[tuple[str, float]]:
    """
    Return the top fuzzy matches for OCR text against a provided candidate list.
    """
    if not ocr_text.strip():
        return []

    matches = process.extract(
        query=ocr_text,
        choices=candidate_names,
        scorer=fuzz.WRatio,
        limit=limit,
    )

    results = []
    for match_name, score, _ in matches:
        results.append((match_name, score))

    return results
