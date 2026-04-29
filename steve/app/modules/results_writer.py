import csv
from pathlib import Path


RESULTS_FILE = Path("output/results/results.csv")


def ensure_results_file() -> None:
    """
    Create the results CSV with headers if it doesn't exist yet.
    """
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if RESULTS_FILE.exists():
        return

    with RESULTS_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            "image_name",
            "ocr_name_guess",
            "chosen_card_name",
            "bottom_strip_raw_text",
            "parsed_set_code_guess",
            "parsed_collector_number_guess",
            "chosen_set_code",
            "chosen_collector_number",
            "final_card_name",
            "final_set_code",
            "final_collector_number",
        ])


def append_result_row(
    image_name: str,
    ocr_name_guess: str,
    chosen_card_name: str,
    bottom_strip_raw_text: str,
    parsed_set_code_guess: str,
    parsed_collector_number_guess: str,
    chosen_set_code: str,
    chosen_collector_number: str,
    final_card_name: str,
    final_set_code: str,
    final_collector_number: str,
) -> None:
    """
    Append one result row to the CSV.
    """
    ensure_results_file()

    with RESULTS_FILE.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            image_name,
            ocr_name_guess,
            chosen_card_name,
            bottom_strip_raw_text,
            parsed_set_code_guess,
            parsed_collector_number_guess,
            chosen_set_code,
            chosen_collector_number,
            final_card_name,
            final_set_code,
            final_collector_number,
        ])
