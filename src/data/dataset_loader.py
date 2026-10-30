"""Local RGB image ingestion; no network access or inferred annotation pairings."""
from __future__ import annotations

import io
import logging
import warnings
from pathlib import Path
from typing import BinaryIO

import numpy as np
import pandas as pd
from PIL import Image, ImageOps, UnidentifiedImageError

LOGGER = logging.getLogger(__name__)
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
SUPPORTED_FORMATS = {"JPEG", "PNG", "TIFF"}
MAX_PIXELS = 40_000_000


def load_image(source: str | Path | bytes | BinaryIO) -> np.ndarray:
    """Load first image/frame as EXIF-oriented uint8 RGB, rejecting >40M pixels.

    TIFF: first page only. Monochrome 16-bit TIFF intensities are linearly mapped
    from the unsigned 16-bit range to 8-bit; thermal units are never inferred.
    Transparent PNGs are composited on white. Invalid inputs raise ValueError.
    """
    if isinstance(source, (str, Path)):
        path = Path(source).expanduser()
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError("Supported image types: JPG, JPEG, PNG, TIF and TIFF.")
        if not path.is_file():
            raise ValueError(f"Image file does not exist: {path}")
        stream = path
    elif isinstance(source, bytes):
        if not source:
            raise ValueError("The image upload is empty.")
        stream = io.BytesIO(source)
    elif hasattr(source, "read"):
        stream = source
        if hasattr(stream, "seek"):
            stream.seek(0)
    else:
        raise ValueError("Provide an image path, uploaded bytes, or a file object.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(stream) as opened:
                if opened.format not in SUPPORTED_FORMATS:
                    raise ValueError("The file content must be JPEG, PNG or TIFF.")
                width, height = opened.size
                if width < 1 or height < 1:
                    raise ValueError("The image has no pixels.")
                if width * height > MAX_PIXELS:
                    raise ValueError("Image exceeds 40 million pixels. Resize or crop locally first.")
                if getattr(opened, "n_frames", 1) > 1:
                    LOGGER.info("Using first frame/page of a multi-frame image.")
                oriented = ImageOps.exif_transpose(opened)
                if oriented.mode.startswith("I;16"):
                    grayscale = (np.asarray(oriented, dtype=np.float32) / 257).clip(0, 255).astype(np.uint8)
                    oriented = Image.fromarray(grayscale)
                if oriented.mode in {"RGBA", "LA"} or "transparency" in oriented.info:
                    rgba = oriented.convert("RGBA")
                    background = Image.new("RGBA", rgba.size, "white")
                    oriented = Image.alpha_composite(background, rgba)
                rgb = np.asarray(oriented.convert("RGB"), dtype=np.uint8).copy()
        return rgb
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError("Image is too large to decode safely. Resize or crop it locally.") from exc
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ValueError("Cannot decode this image. Check that it is a valid supported file.") from exc


def list_images(folder: str | Path, recursive: bool = True) -> list[Path]:
    """Return supported local files in stable order without loading them."""
    directory = Path(folder).expanduser()
    if not directory.is_dir():
        raise ValueError(f"Image folder does not exist: {directory}")
    entries = directory.rglob("*") if recursive else directory.glob("*")
    return sorted((p for p in entries if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS), key=lambda p: str(p).lower())


def inspect_dataset(folder: str | Path) -> pd.DataFrame:
    """Inspect actual files and headers; never infer masks, labels or pairings."""
    records = []
    for path in list_images(folder):
        row = {"path": str(path.resolve()), "width": None, "height": None,
               "mode": None, "format": None, "loadable": False, "error": ""}
        try:
            with Image.open(path) as image:
                row.update(width=image.width, height=image.height, mode=image.mode, format=image.format)
            oriented_rgb = load_image(path)
            row.update(width=oriented_rgb.shape[1], height=oriented_rgb.shape[0])
            row["loadable"] = True
        except (ValueError, OSError, Image.DecompressionBombError) as exc:
            row["error"] = str(exc)
        records.append(row)
    return pd.DataFrame(records, columns=["path", "width", "height", "mode", "format", "loadable", "error"])
