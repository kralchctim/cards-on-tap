from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter


def load_image(image_path: Path) -> Image.Image:
    """
    Open an image file and return the Pillow image object.
    """
    return Image.open(image_path)


def print_image_info(image: Image.Image, image_path: Path) -> None:
    """
    Print basic information about the image.
    """
    print("\n=== Image Info ===")
    print(f"File: {image_path}")
    print(f"Format: {image.format}")
    print(f"Size: {image.width} x {image.height}")
    print(f"Mode: {image.mode}")


def save_debug_copy(image: Image.Image, original_path: Path) -> Path:
    """
    Save a copy of the image into output/debug.
    """
    debug_dir = Path("output/debug")
    debug_dir.mkdir(parents=True, exist_ok=True)

    output_path = debug_dir / f"debug_{original_path.name}"
    image.save(output_path)

    return output_path


def crop_center(image: Image.Image, crop_width_ratio: float = 0.5, crop_height_ratio: float = 0.5) -> Image.Image:
    """
    Crop the center portion of the image.
    """
    width, height = image.size

    crop_width = int(width * crop_width_ratio)
    crop_height = int(height * crop_height_ratio)

    left = (width - crop_width) // 2
    top = (height - crop_height) // 2
    right = left + crop_width
    bottom = top + crop_height

    return image.crop((left, top, right, bottom))


def save_cropped_image(cropped_image: Image.Image, original_path: Path) -> Path:
    """
    Save a cropped version of the image into output/debug.
    """
    debug_dir = Path("output/debug")
    debug_dir.mkdir(parents=True, exist_ok=True)

    output_path = debug_dir / f"cropped_{original_path.name}"
    cropped_image.save(output_path)

    return output_path


def crop_name_region(image: Image.Image) -> Image.Image:
    """
    Crop a tighter top band of the card where the card name usually appears.

    This version trims a little from the left and right edges,
    and is shorter in height to avoid pulling in too much of the art box.
    """
    width, height = image.size

    left = int(width * 0.03)
    top = int(height * 0.02)
    right = int(width * 0.95)
    bottom = int(height * 0.14)

    return image.crop((left, top, right, bottom))


def save_name_region_image(name_region: Image.Image, original_path: Path) -> Path:
    """
    Save the cropped name region into output/debug.
    """
    debug_dir = Path("output/debug")
    debug_dir.mkdir(parents=True, exist_ok=True)

    output_path = debug_dir / f"name_region_{original_path.name}"
    name_region.save(output_path)

    return output_path


def preprocess_for_ocr(image: Image.Image) -> Image.Image:
    """
    Apply simple preprocessing to help OCR:
    - convert to grayscale
    - increase contrast
    - sharpen slightly
    """
    grayscale = image.convert("L")

    contrast_enhancer = ImageEnhance.Contrast(grayscale)
    high_contrast = contrast_enhancer.enhance(2.0)

    sharpened = high_contrast.filter(ImageFilter.SHARPEN)

    return sharpened


def save_preprocessed_image(image: Image.Image, original_path: Path) -> Path:
    """
    Save the OCR-preprocessed image into output/debug.
    """
    debug_dir = Path("output/debug")
    debug_dir.mkdir(parents=True, exist_ok=True)

    output_path = debug_dir / f"preprocessed_{original_path.name}"
    image.save(output_path)

    return output_path


def crop_set_code_region(image: Image.Image) -> Image.Image:
    """
    Crop the bottom-left band where collector number, set code,
    rarity, and language usually appear on modern cards.
    """
    width, height = image.size

    left = int(width * 0.02)
    top = int(height * 0.93)
    right = int(width * 0.38)
    bottom = int(height * 0.995)

    return image.crop((left, top, right, bottom))


def save_set_code_region_image(set_code_region: Image.Image, original_path: Path) -> Path:
    """
    Save the cropped set-code region into output/debug.
    """
    debug_dir = Path("output/debug")
    debug_dir.mkdir(parents=True, exist_ok=True)

    output_path = debug_dir / f"set_code_region_{original_path.name}"
    set_code_region.save(output_path)

    return output_path
