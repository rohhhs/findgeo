# Required libraries:
# pip install pillow numpy

from PIL import Image, JpegImagePlugin
import os
import numpy as np
from typing import Optional

from ..definitions import *

def DefineImageQuality(imagePath: str) -> str:
    """
    Heuristic image quality classifier.
    Returns one of: 'low', 'medium', 'high', 'original'.
    Uses file size, pixel dimensions, simple sharpness metric and (for JPEG) quantization tables to estimate quality.
    The thresholds are conservative and intended for general-purpose automated workflows; tune if needed.
    """
    if not os.path.isfile(imagePath):
        raise FileNotFoundError(f"No such file: {imagePath}")

    # Basic file / image properties
    file_size = os.path.getsize(imagePath)            # bytes
    file_kb = file_size / 1024.0
    try:
        img = Image.open(imagePath)
    except Exception as e:
        raise ValueError(f"Cannot open image '{imagePath}': {e}")

    # handle animated / multi-frame by using first frame
    try:
        img.seek(0)
    except Exception:
        pass

    fmt: Optional[str] = img.format
    width, height = img.size
    megapixels = (width * height) / 1_000_000.0

    # ---------- sharpness metric (fast, lightweight) ----------
    # convert to greyscale and compute simple gradient variance as a proxy for focus/detail
    try:
        gray = np.asarray(img.convert("L"), dtype=np.float32)
        # horizontal and vertical absolute differences
        gx = np.abs(np.diff(gray, axis=1))
        gy = np.abs(np.diff(gray, axis=0))
        # variance of gradients (gives larger values for sharper / more detailed images)
        sharpness = float(np.var(gx)) + float(np.var(gy))
    except Exception:
        sharpness = 0.0

    # ---------- JPEG quantization based quality estimate (if available) ----------
    jpeg_quality_est = None
    if fmt and fmt.upper() == "JPEG":
        try:
            # PIL stores quantization tables in img.quantization (a dict) for JPEGs
            qtables = getattr(img, "quantization", None)
            if qtables:
                # qtables can be a dict mapping idx->list
                if isinstance(qtables, dict):
                    means = []
                    for tbl in qtables.values():
                        arr = np.asarray(tbl, dtype=np.float32)
                        means.append(float(np.mean(arr)))
                    mean_q = float(np.mean(means)) if means else None
                else:
                    # fallback if it's a list/tuple of tables
                    arrs = [np.asarray(t, dtype=np.float32) for t in qtables]
                    mean_q = float(np.mean([a.mean() for a in arrs])) if arrs else None

                if mean_q and mean_q > 0:
                    # heuristic inversion: lower quant-table means higher quality
                    # mapping formula commonly used (approx): quality ≈ round(5000 / mean_q)
                    est = int(round(5000.0 / mean_q))
                    jpeg_quality_est = max(1, min(100, est))
        except Exception:
            jpeg_quality_est = None

    # ---------- Heuristic decision rules ----------
    # Tunable thresholds (conservative defaults):
    # megapixel thresholds
    MP_ORIGINAL = 8.0    # >= 8MP considered high-res original candidate
    MP_HIGH = 4.0        # >= 4MP considered high
    MP_MED = 1.0         # >= 1MP considered medium

    # file size thresholds (KB)
    KB_ORIGINAL = 2000.0
    KB_HIGH = 800.0
    KB_MED = 200.0

    # sharpness thresholds (empirical, depends on image content)
    SHARP_HIGH = 50.0
    SHARP_MED = 10.0

    # JPEG quality thresholds
    if jpeg_quality_est is not None:
        if jpeg_quality_est >= 90 and megapixels >= MP_ORIGINAL and file_kb >= KB_ORIGINAL:
            return "original"
        if jpeg_quality_est >= 80 and (megapixels >= MP_HIGH or file_kb >= KB_HIGH) and sharpness >= SHARP_MED:
            return "high"
        if jpeg_quality_est >= 60 and (megapixels >= MP_MED or file_kb >= KB_MED):
            return "medium"
        # fall through to low if JPEG quality estimate is small
        return "low"

    # Non-JPEG heuristic (PNG, TIFF, WEBP, GIF, BMP, etc.)
    fmt_upper = (fmt or "").upper()
    if fmt_upper in ("PNG", "TIFF"):
        # lossless formats: assume original unless very small/resized or extremely low sharpness
        if megapixels >= MP_HIGH and file_kb >= KB_HIGH:
            return "original"
        if megapixels >= MP_MED or file_kb >= KB_MED:
            return "high"
        return "medium" if megapixels > 0.2 else "low"

    # WEBP may be lossy or lossless; treat similarly to JPEG/PNG mix using file size and sharpness
    if fmt_upper == "WEBP":
        if megapixels >= MP_ORIGINAL and file_kb >= KB_ORIGINAL and sharpness >= SHARP_HIGH:
            return "original"
        if megapixels >= MP_HIGH and file_kb >= KB_HIGH:
            return "high"
        if megapixels >= MP_MED:
            return "medium"
        return "low"

    # Generic fallback for unknown/other formats or if we couldn't compute anything meaningful
    score = 0
    if megapixels >= MP_ORIGINAL: score += 3
    elif megapixels >= MP_HIGH: score += 2
    elif megapixels >= MP_MED: score += 1

    if file_kb >= KB_ORIGINAL: score += 3
    elif file_kb >= KB_HIGH: score += 2
    elif file_kb >= KB_MED: score += 1

    if sharpness >= SHARP_HIGH: score += 2
    elif sharpness >= SHARP_MED: score += 1

    # score: 0..8 roughly
    if score >= 6:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


# ----------------- Example usage -----------------
if __name__ == "__main__":
    # Example (integrates with the user's pseudo-code pattern)
    import os

    # simple standalone call
    path = os.path.join(ASSET_IMAGE_DATABASE001_PATH, "0a0ee2fb-b7ad-4430-97d7-281e2c293041.jpg")
    print("Quality:", DefineImageQuality(path))

    # Example integration in a CSV row loop (pseudo)
    # for image_filename, quality in par_
