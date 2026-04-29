from pathlib import Path
from typing import Optional
from functools import lru_cache

from PIL import Image


def _center_crop(image: Image.Image, crop_width_ratio: float, crop_height_ratio: float) -> Image.Image:
    width, height = image.size

    crop_width = max(1, int(width * crop_width_ratio))
    crop_height = max(1, int(height * crop_height_ratio))

    left = max(0, (width - crop_width) // 2)
    top = max(0, (height - crop_height) // 2)
    right = min(width, left + crop_width)
    bottom = min(height, top + crop_height)

    return image.crop((left, top, right, bottom))


def _orient_card_portrait(card_image: Image.Image) -> Image.Image:
    """
    Ensure card crop is portrait-oriented for downstream percentage crops.
    """
    width, height = card_image.size
    if width > height:
        # PIL rotates counter-clockwise for positive angles, so -90 is clockwise.
        return card_image.rotate(-90, expand=True)
    return card_image


@lru_cache(maxsize=4)
def _load_yolo_model_cached(model_path_str: str):
    try:
        from ultralytics import YOLO
    except ImportError:
        return None

    model_path = Path(model_path_str)
    if not model_path.exists():
        return None

    return YOLO(str(model_path))


def _load_yolo_model(model_path: Path):
    # Keep a small cache so batch processing doesn't reload 50-200MB weights repeatedly.
    # Keying by absolute path avoids duplicate loads from different working directories.
    return _load_yolo_model_cached(str(model_path.expanduser().resolve()))


def detect_card_and_crop(
    image: Image.Image,
    model_path: str = "models/card_detector.pt",
    confidence_threshold: float = 0.25,
) -> Optional[Image.Image]:
    """
    Detect a card in the image and return the best cropped region.

    Returns None if no model is available or no confident detection is found.
    """
    model = _load_yolo_model(Path(model_path))
    if model is None:
        return None

    rgb_image = image.convert("RGB")
    results = model.predict(source=rgb_image, conf=confidence_threshold, verbose=False)
    if not results:
        return None

    result = results[0]
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return None

    best_index = int(boxes.conf.argmax().item())
    x1, y1, x2, y2 = boxes.xyxy[best_index].tolist()

    width, height = rgb_image.size
    left = max(0, int(x1))
    top = max(0, int(y1))
    right = min(width, int(x2))
    bottom = min(height, int(y2))

    if right <= left or bottom <= top:
        return None

    card_crop = rgb_image.crop((left, top, right, bottom))
    return _orient_card_portrait(card_crop)


def preprocess_image_with_card_detection(
    image: Image.Image,
    model_path: str = "models/card_detector.pt",
    confidence_threshold: float = 0.25,
) -> Image.Image:
    """
    Return a card-only crop for downstream percentage-based regions.

    - If YOLO detects a card: return the YOLO crop.
    - If YOLO is unavailable / no detection: return a center crop as a best-effort fallback.
    """
    detected_crop = detect_card_and_crop(
        image=image,
        model_path=model_path,
        confidence_threshold=confidence_threshold,
    )

    if detected_crop is None:
        return _center_crop(image.convert("RGB"), crop_width_ratio=0.6, crop_height_ratio=0.9)

    return detected_crop
