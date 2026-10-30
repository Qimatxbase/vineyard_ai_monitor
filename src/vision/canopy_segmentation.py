"""Colour-based visible vegetation segmentation; no species diagnosis is implied."""
import cv2
import numpy as np

from config import AnalysisConfig


def validate_rgb(image: np.ndarray) -> np.ndarray:
    if not isinstance(image, np.ndarray) or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Expected an RGB image with shape (height, width, 3).")
    if image.size == 0:
        raise ValueError("Image must contain pixels.")
    if image.dtype != np.uint8:
        raise ValueError("RGB image must use uint8 values from 0 to 255.")
    return np.ascontiguousarray(image)


def excess_green(image: np.ndarray) -> np.ndarray:
    rgb = image.astype(np.float32) / 255.0
    return 2.0 * rgb[..., 1] - rgb[..., 0] - rgb[..., 2]


def _raw_mask(image: np.ndarray, config: AnalysisConfig, otsu_threshold: float | None = None) -> np.ndarray:
    exg = excess_green(image)
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    hue_ok = (hsv[..., 0] >= config.hue_min) & (hsv[..., 0] <= config.hue_max)
    hsv_mask = hue_ok & (hsv[..., 1] >= config.saturation_min) & (hsv[..., 2] >= 25)
    exg_mask = (exg > config.exg_threshold) & (hsv[..., 2] >= 25)
    if config.segmentation_mode == "hsv":
        return hsv_mask
    if config.segmentation_mode == "exg":
        return exg_mask
    if config.segmentation_mode == "otsu":
        exg_u8 = np.clip((exg + 2) * 63.75, 0, 255).astype(np.uint8)
        if otsu_threshold is None:
            _, thresholded = cv2.threshold(exg_u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
            thresholded = exg_u8 > otsu_threshold
        return (thresholded > 0) & (exg > config.exg_threshold) & hsv_mask
    # Include yellow-green canopy, but require a vegetation-compatible hue for ExG.
    return hsv_mask | (exg_mask & hue_ok & (hsv[..., 1] >= config.saturation_min // 2))


def segment_canopy(image: np.ndarray, config: AnalysisConfig | None = None) -> np.ndarray:
    """Return a Boolean mask. Optional tiles bound feature-array memory, not image scale."""
    config = config or AnalysisConfig()
    image = validate_rgb(image)
    height, width = image.shape[:2]
    if config.tile_size:
        mask = np.zeros((height, width), dtype=np.uint8)
        otsu_threshold = None
        if config.segmentation_mode == "otsu":
            # Share one image-wide threshold so tile boundaries do not change
            # segmentation. A histogram pass avoids a full-frame float buffer.
            histogram = np.zeros(256, dtype=np.float64)
            for y in range(0, height, config.tile_size):
                for x in range(0, width, config.tile_size):
                    patch_exg = excess_green(image[y:y + config.tile_size, x:x + config.tile_size])
                    encoded = np.clip((patch_exg + 2) * 63.75, 0, 255).astype(np.uint8)
                    histogram += np.bincount(encoded.ravel(), minlength=256)
            cumulative = np.cumsum(histogram)
            weighted = np.cumsum(histogram * np.arange(256))
            denominator = cumulative * (cumulative[-1] - cumulative)
            separation = np.zeros(256, dtype=np.float64)
            valid = denominator > 0
            separation[valid] = ((weighted[-1] * cumulative[valid] - weighted[valid] * cumulative[-1]) ** 2
                                 / denominator[valid])
            otsu_threshold = float(np.argmax(separation))
        for y in range(0, height, config.tile_size):
            for x in range(0, width, config.tile_size):
                patch = image[y:y + config.tile_size, x:x + config.tile_size]
                mask[y:y + config.tile_size, x:x + config.tile_size] = _raw_mask(patch, config, otsu_threshold)
    else:
        mask = _raw_mask(image, config).astype(np.uint8)
    # Filtering happens after assembling tiles, avoiding seams at tile boundaries.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (config.morphology_size,) * 2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    if config.min_component_area:
        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        keep = np.zeros(count, dtype=bool)
        keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= config.min_component_area
        mask = keep[labels]
    return mask.astype(bool)
