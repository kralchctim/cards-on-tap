from app.modules.bottom_strip_parser import parse_bottom_strip_text

from app.modules.image_utils import (
    load_image,
    print_image_info,
    save_debug_copy,
    crop_center,
    save_cropped_image,
    crop_name_region,
    save_name_region_image,
    preprocess_for_ocr,
    save_preprocessed_image,
    crop_set_code_region,
    save_set_code_region_image,
)
from app.modules.identify_card import get_image_paths, choose_card_name
from app.modules.image_utils import (
    load_image,
    print_image_info,
    save_debug_copy,
    crop_center,
    save_cropped_image,
    crop_name_region,
    save_name_region_image,
    preprocess_for_ocr,
    save_preprocessed_image,
)
from app.modules.ocr_utils import (
    clean_ocr_text,
    extract_best_name_guess,
    run_all_ocr_variants,
    choose_best_ocr_result,
)
from app.modules.card_name_matcher import get_top_name_matches
from app.modules.candidate_list import get_candidate_names
from app.modules.scryfall_lookup import get_best_card, get_card_by_set_and_number, print_card_summary
from app.modules.printings_loader import (
    load_printings,
    get_sets_for_name,
    get_collector_numbers_for_name_and_set,
)

from app.modules.token_matcher import get_top_token_matches
from app.modules.bottom_strip_parser import parse_bottom_strip_text
from app.modules.printings_loader import (
    load_printings,
    get_sets_for_name,
    get_collector_numbers_for_name_and_set,
    get_normalized_collector_numbers_for_name_and_set,
    normalize_collector_number,
)
from app.modules.printing_selector import choose_from_matches

from app.modules.results_writer import ensure_results_file, append_result_row
from app.modules.detect_and_crop import preprocess_image_with_card_detection

def process_image(image_path, candidate_names, printings):
    print("\n" + "=" * 60)
    print(f"Processing image: {image_path.name}")
    print("=" * 60)

    image = load_image(image_path)
    processed_image = preprocess_image_with_card_detection(image)
    print_image_info(processed_image, image_path)

    debug_path = save_debug_copy(processed_image, image_path)
    print(f"Debug copy saved to: {debug_path}")

    cropped_image = crop_center(processed_image, crop_width_ratio=0.5, crop_height_ratio=0.5)
    cropped_path = save_cropped_image(cropped_image, image_path)
    print(f"Cropped image saved to: {cropped_path}")

    name_region = crop_name_region(processed_image)
    name_region_path = save_name_region_image(name_region, image_path)
    print(f"Name region image saved to: {name_region_path}")

    preprocessed_name_region = preprocess_for_ocr(name_region)
    preprocessed_path = save_preprocessed_image(preprocessed_name_region, image_path)
    print(f"Preprocessed image saved to: {preprocessed_path}")

    set_code_region = crop_set_code_region(processed_image)
    set_code_region_path = save_set_code_region_image(set_code_region, image_path)
    print(f"Set code region image saved to: {set_code_region_path}")

    print("\n=== OCR Variants on bottom strip region ===")
    bottom_strip_results = run_all_ocr_variants(set_code_region)
    for variant, text in bottom_strip_results.items():
        print(f"{variant}: {repr(text)}")

    best_bottom_variant, best_bottom_raw_text = choose_best_ocr_result(bottom_strip_results)
    parsed_bottom = parse_bottom_strip_text(best_bottom_raw_text)

    print("\n=== Best Bottom Strip OCR Result ===")
    print(f"Best variant: {best_bottom_variant}")
    print(f"Best raw OCR text: {best_bottom_raw_text}")
    print(f"Parsed bottom strip: {parsed_bottom}")

    print("\n=== OCR Variants on RAW name region ===")
    raw_results = run_all_ocr_variants(name_region)
    for variant, text in raw_results.items():
        print(f"{variant}: {repr(text)}")

    best_variant, best_raw_text = choose_best_ocr_result(raw_results)
    cleaned_best_text = clean_ocr_text(best_raw_text)
    best_guess = extract_best_name_guess(best_raw_text)

    print("\n=== Best OCR Result ===")
    print(f"Best variant: {best_variant}")
    print(f"Best raw OCR text: {best_raw_text}")
    print(f"Cleaned best OCR text: {cleaned_best_text}")
    print(f"Best OCR name guess: {best_guess}")

    top_matches = get_top_name_matches(best_guess, candidate_names, limit=3)
    chosen_card_name = choose_card_name(top_matches)

    # OCR + parse the bottom strip
    print("\n=== OCR Variants on bottom strip region ===")
    bottom_strip_results = run_all_ocr_variants(set_code_region)
    for variant, text in bottom_strip_results.items():
        print(f"{variant}: {repr(text)}")

    best_bottom_variant, best_bottom_raw_text = choose_best_ocr_result(bottom_strip_results)
    parsed_bottom = parse_bottom_strip_text(best_bottom_raw_text)

    print("\n=== Best Bottom Strip OCR Result ===")
    print(f"Best variant: {best_bottom_variant}")
    print(f"Best raw OCR text: {best_bottom_raw_text}")
    print(f"Parsed bottom strip: {parsed_bottom}")

    # Now resolve the exact printing
    set_codes = get_sets_for_name(chosen_card_name, printings)

    if len(set_codes) == 1:
        chosen_set = set_codes[0]
        print(f"Only one set available: {chosen_set}")
    else:
        set_guess = parsed_bottom.get("set_code", "")
        top_set_matches = get_top_token_matches(set_guess, set_codes, limit=3)
        chosen_set = choose_from_matches("set code", top_set_matches)

    collector_numbers = get_collector_numbers_for_name_and_set(chosen_card_name, chosen_set, printings)

    if len(collector_numbers) == 1:
        chosen_collector_number = collector_numbers[0]
        print(f"Only one collector number available: {chosen_collector_number}")
    else:
        collector_guess = parsed_bottom.get("collector_number", "")
        normalized_candidates = get_normalized_collector_numbers_for_name_and_set(
            chosen_card_name,
            chosen_set,
            printings
        )
        normalized_guess = normalize_collector_number(collector_guess)

        top_collector_matches = get_top_token_matches(
            normalized_guess,
            normalized_candidates,
            limit=3
        )
        chosen_collector_number = choose_from_matches("collector number", top_collector_matches)

    exact_card = get_card_by_set_and_number(chosen_set, chosen_collector_number)

    final_card_name = ""
    final_set_code = ""
    final_collector_number = ""

    if exact_card:
        print_card_summary(exact_card)
        final_card_name = exact_card.get("name", "")
        final_set_code = exact_card.get("set", "")
        final_collector_number = exact_card.get("collector_number", "")
    else:
        print("\nCould not fetch exact printing. Falling back to name-only lookup.")
        fallback_card = get_best_card(chosen_card_name)
        print_card_summary(fallback_card)

        if fallback_card:
            final_card_name = fallback_card.get("name", "")
            final_set_code = fallback_card.get("set", "")
            final_collector_number = fallback_card.get("collector_number", "")

    append_result_row(
        image_name=image_path.name,
        ocr_name_guess=best_guess,
        chosen_card_name=chosen_card_name,
        bottom_strip_raw_text=best_bottom_raw_text,
        parsed_set_code_guess=parsed_bottom.get("set_code", ""),
        parsed_collector_number_guess=parsed_bottom.get("collector_number", ""),
        chosen_set_code=chosen_set,
        chosen_collector_number=chosen_collector_number,
        final_card_name=final_card_name,
        final_set_code=final_set_code,
        final_collector_number=final_collector_number,
    )

def main():
    print("MTG card lookup from images folder")

    try:
        candidate_names = get_candidate_names()
        printings = load_printings()
        image_paths = get_image_paths()
        ensure_results_file()

        print(f"\nFound {len(image_paths)} image(s) in input/images")

        for image_path in image_paths:
            process_image(image_path, candidate_names, printings)

    except Exception as e:
        print(f"\nSomething went wrong: {e}")


if __name__ == "__main__":
    main()
