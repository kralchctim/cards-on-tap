from pathlib import Path

from app.modules.image_utils import (
    load_image,
    crop_name_region,
    crop_set_code_region,
)
from app.modules.detect_and_crop import preprocess_image_with_card_detection
from app.modules.ocr_utils import (
    extract_best_name_guess,
    run_all_ocr_variants,
    choose_best_ocr_result,
)
from app.modules.card_name_matcher import get_top_name_matches
from app.modules.bottom_strip_parser import parse_bottom_strip_text
from app.modules.printings_loader import (
    load_printings,
    get_sets_for_name,
    get_normalized_collector_numbers_for_name_and_set,
    normalize_collector_number,
)
from app.modules.token_matcher import get_top_token_matches


def scan_image_for_name(image_path: Path, candidate_names: list[str]) -> dict:
    """
    Run the name-identification part of the pipeline for one image,
    plus bottom-strip OCR/parsing, set-code matching, and collector-number
    matching for UI debugging.
    """
    image = load_image(image_path)
    processed_image = preprocess_image_with_card_detection(image)

    # Name region
    name_region = crop_name_region(processed_image)
    name_raw_results = run_all_ocr_variants(name_region)
    name_best_variant, name_best_raw_text = choose_best_ocr_result(name_raw_results)
    name_best_guess = extract_best_name_guess(name_best_raw_text)
    top_matches = get_top_name_matches(name_best_guess, candidate_names, limit=3)

    # Bottom strip region
    bottom_strip_region = crop_set_code_region(processed_image)
    bottom_raw_results = run_all_ocr_variants(bottom_strip_region)
    bottom_best_variant, bottom_best_raw_text = choose_best_ocr_result(bottom_raw_results)
    parsed_bottom = parse_bottom_strip_text(bottom_best_raw_text)

    # Debug path for printing resolution
    chosen_card_name_for_debug = top_matches[0][0] if top_matches else ""
    set_top_matches = []
    chosen_set_for_debug = ""
    collector_top_matches = []

    if chosen_card_name_for_debug:
        printings = load_printings()

        valid_set_codes = get_sets_for_name(chosen_card_name_for_debug, printings)
        parsed_set_guess = parsed_bottom.get("set_code", "")
        set_top_matches = get_top_token_matches(parsed_set_guess, valid_set_codes, limit=3)

        if set_top_matches:
            chosen_set_for_debug = set_top_matches[0][0]

        if chosen_set_for_debug:
            parsed_collector_guess = parsed_bottom.get("collector_number", "")
            normalized_guess = normalize_collector_number(parsed_collector_guess)

            valid_collector_numbers = get_normalized_collector_numbers_for_name_and_set(
                chosen_card_name_for_debug,
                chosen_set_for_debug,
                printings,
            )

            collector_top_matches = get_top_token_matches(
                normalized_guess,
                valid_collector_numbers,
                limit=3,
            )

    return {
        "name_region_image": name_region,
        "best_variant": name_best_variant,
        "best_raw_text": name_best_raw_text,
        "best_guess": name_best_guess,
        "top_matches": top_matches,
        "bottom_strip_image": bottom_strip_region,
        "bottom_best_variant": bottom_best_variant,
        "bottom_best_raw_text": bottom_best_raw_text,
        "parsed_bottom": parsed_bottom,
        "chosen_card_name_for_debug": chosen_card_name_for_debug,
        "set_top_matches": set_top_matches,
        "chosen_set_for_debug": chosen_set_for_debug,
        "collector_top_matches": collector_top_matches,
    }
