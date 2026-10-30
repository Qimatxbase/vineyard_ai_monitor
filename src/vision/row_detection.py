"""Infer repeated parallel vegetation bands using orientation-normalised projections."""
import cv2
import numpy as np


def _runs(values: np.ndarray) -> list[tuple[int, int]]:
    edges = np.diff(np.r_[False, values.astype(bool), False].astype(np.int8))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))


def detect_rows(mask: np.ndarray) -> dict:
    """Return supported row bands, abstaining when repeated structure is unclear.

    Angles are clockwise from image +x, because image +y points down. Row normal
    coordinates satisfy n = -sin(angle)*x + cos(angle)*y. This is pixel geometry.
    """
    unavailable = {"available": False, "angle_degrees": None, "confidence": 0.0,
                   "message": "Insufficient repeated row structure; canopy-gap detection is unavailable.",
                   "rows": []}
    height, width = mask.shape
    if np.count_nonzero(mask) < 100 or mask.mean() > 0.88 or min(height, width) < 32:
        return unavailable
    scale = min(1.0, 384.0 / max(height, width))
    small = cv2.resize(mask.astype(np.uint8), (max(2, round(width * scale)), max(2, round(height * scale))), interpolation=cv2.INTER_NEAREST)
    sy, sx = np.indices(small.shape, dtype=np.float32)
    x, y, vegetation = sx.ravel(), sy.ravel(), small.ravel().astype(np.float32)
    scans = []
    for angle in np.arange(0, 180, 2, dtype=float):
        radians = np.deg2rad(angle)
        normal = -np.sin(radians) * x + np.cos(radians) * y
        offset = float(np.floor(normal.min()))
        bins = np.rint(normal - offset).astype(np.int32)
        support = np.bincount(bins)
        profile = np.bincount(bins, weights=vegetation, minlength=len(support)) / np.maximum(support, 1)
        profile = cv2.GaussianBlur(profile.astype(np.float32).reshape(1, -1), (0, 0), 1.3).ravel()
        valid = support >= 0.40 * support.max()
        scores = profile[valid]
        score = float(np.var(scores)) if len(scores) else 0.0
        scans.append((score, float(angle), profile, valid, offset))
    best = max(scans, key=lambda item: item[0])
    score, angle, profile, valid, offset = best
    median_score = float(np.median([item[0] for item in scans]))
    contrast = float(np.percentile(profile[valid], 90) - np.percentile(profile[valid], 20))
    anisotropy = score / max(median_score, 1e-5)
    threshold = max(0.12, float(np.mean(profile[valid]) + 0.20 * np.std(profile[valid])))
    bands = [(a, b) for a, b in _runs((profile >= threshold) & valid) if b - a >= 2]
    if len(bands) < 2 or contrast < 0.18 or anisotropy < 2.5:
        return unavailable
    # Require several rows of comparable width; isolated blobs are not vineyard structure.
    widths = np.array([b - a for a, b in bands], dtype=float)
    median_width = float(np.median(widths))
    bands = [(a, b) for a, b in bands if 0.35 * median_width <= b - a <= 2.8 * median_width]
    if len(bands) < 2:
        return unavailable
    rows = []
    for index, (a, b) in enumerate(bands):
        rows.append({"row_id": index + 1, "normal_center": float(((a + b - 1) / 2 + offset) / scale),
                     "width": float(max(3.0, (b - a) / scale)),
                     "normal_start": float((a + offset) / scale),
                     "normal_end": float((b + offset) / scale)})
    confidence = float(np.clip(0.45 + 0.08 * (anisotropy - 2.5) + 0.25 * contrast, 0, 0.97))
    return {"available": True, "angle_degrees": angle, "confidence": confidence,
            "message": f"{len(rows)} parallel vegetation bands support candidate canopy-gap inspection. Row identity is heuristic.",
            "rows": rows, "projection_contrast": contrast, "orientation_anisotropy": anisotropy}
