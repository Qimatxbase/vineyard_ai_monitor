"""Resizing and tiling with explicit original-image coordinate mapping."""
from __future__ import annotations

import cv2
import numpy as np


def prepare_image(image: np.ndarray, max_dimension: int = 1600) -> tuple[np.ndarray, dict]:
    """Resize without upsampling; original_x = processed_x * scale_x (and y)."""
    if not isinstance(image, np.ndarray) or image.ndim != 3 or image.shape[2] != 3 or image.size == 0:
        raise ValueError("Expected a non-empty H×W×3 RGB image.")
    if image.dtype != np.uint8:
        raise ValueError("Expected uint8 RGB pixels.")
    if max_dimension < 1:
        raise ValueError("max_dimension must be positive.")
    height, width = image.shape[:2]
    scale = min(1.0, max_dimension / max(height, width))
    processed_width, processed_height = max(1, round(width * scale)), max(1, round(height * scale))
    resized = cv2.resize(image, (processed_width, processed_height), interpolation=cv2.INTER_AREA) if scale < 1 else image.copy()
    return resized, {"original_width": width, "original_height": height,
                     "processed_width": processed_width, "processed_height": processed_height,
                     "scale_x": width / processed_width, "scale_y": height / processed_height}


def iter_tiles(image: np.ndarray, tile_size: int = 512, overlap: int = 0):
    """Yield ((x1,y1,x2,y2), tile) with half-open image-relative pixel bounds.

    Border tiles may be smaller. Overlapping tiles must be merged by the caller;
    coordinates always refer to the supplied image, not to an original source.
    """
    if not isinstance(image, np.ndarray) or image.ndim < 2 or image.size == 0:
        raise ValueError("Expected a non-empty image array.")
    if tile_size < 1 or not 0 <= overlap < tile_size:
        raise ValueError("Require tile_size > 0 and 0 <= overlap < tile_size.")
    height, width = image.shape[:2]
    step = tile_size - overlap
    for y1 in range(0, height, step):
        for x1 in range(0, width, step):
            x2, y2 = min(x1 + tile_size, width), min(y1 + tile_size, height)
            yield (x1, y1, x2, y2), image[y1:y2, x1:x2]
