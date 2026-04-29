import re
from PIL import Image
import pytesseract


def upscale_image(image: Image.Image, scale: int = 2) -> Image.Image:
    """
    Make the image larger to help OCR.
    """
    return image.resize((image.width * scale, image.height * scale))


def extract_text_default(image: Image.Image) -> str:
    text = pytesseract.image_to_string(image)
    return text.strip()


def extract_text_psm6(image: Image.Image) -> str:
    text = pytesseract.image_to_string(image, config="--psm 6")
    return text.strip()


def extract_text_psm7(image: Image.Image) -> str:
    text = pytesseract.image_to_string(image, config="--psm 7")
    return text.strip()


def clean_ocr_text(text: str) -> str:
    """
    Basic cleanup:
    - replace line breaks with spaces
    - remove weird punctuation
    - collapse repeated whitespace
    """
    text = text.strip()
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"[^A-Za-z0-9\s'\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_best_name_guess(text: str) -> str:
    """
    Try to pull out the most card-name-like chunk from OCR text.

    Strategy:
    - clean the text
    - split into words
    - keep only words that look name-like
    - build short runs of consecutive name-like words
    - prefer the last sensible run
    """
    text = clean_ocr_text(text)

    if not text:
        return ""

    words = text.split()

    def is_name_like(word: str) -> bool:
        if not word:
            return False

        # Accept words that start uppercase, or contain hyphens/apostrophes
        if word[0].isupper() or "-" in word or "'" in word:
            return True

        return False

    runs = []
    current_run = []

    for word in words:
        if is_name_like(word):
            current_run.append(word)
        else:
            if current_run:
                runs.append(current_run)
                current_run = []

    if current_run:
        runs.append(current_run)

    if not runs:
        return text

    # Trim obviously trailing junk from each run
    trimmed_runs = []
    for run in runs:
        trimmed = run[:]

        # Drop short trailing junk like "Le" or "uy"
        while trimmed and len(trimmed[-1]) <= 2 and "-" not in trimmed[-1] and "'" not in trimmed[-1]:
            trimmed.pop()

        if trimmed:
            trimmed_runs.append(trimmed)

    if not trimmed_runs:
        trimmed_runs = runs

    # Prefer the last run, but keep it to a max of 4 words
    best_run = trimmed_runs[-1]
    best_run = best_run[-4:]

    return " ".join(best_run)

def score_ocr_text(text: str) -> int:
    """
    Very rough scoring:
    - longer cleaned text is better than blank
    - title-like words get a boost
    """
    cleaned = clean_ocr_text(text)
    if not cleaned:
        return 0

    score = len(cleaned)

    words = cleaned.split()
    for word in words:
        if word and word[0].isupper():
            score += 5
        if "-" in word or "'" in word:
            score += 3

    return score


def run_all_ocr_variants(image: Image.Image) -> dict:
    """
    Try several OCR variants and return all results.
    """
    upscaled = upscale_image(image, scale=2)

    results = {
        "default": extract_text_default(image),
        "psm6": extract_text_psm6(image),
        "psm7": extract_text_psm7(image),
        "default_upscaled": extract_text_default(upscaled),
        "psm6_upscaled": extract_text_psm6(upscaled),
        "psm7_upscaled": extract_text_psm7(upscaled),
    }

    return results


def choose_best_ocr_result(results: dict) -> tuple[str, str]:
    """
    Return (variant_name, raw_text) for the best OCR result.
    """
    best_variant = ""
    best_text = ""
    best_score = -1

    for variant_name, raw_text in results.items():
        score = score_ocr_text(raw_text)
        if score > best_score:
            best_score = score
            best_variant = variant_name
            best_text = raw_text

    return best_variant, best_text
