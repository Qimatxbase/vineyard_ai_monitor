"""Find unusually long interior gaps along supported vegetation rows."""
import cv2
import numpy as np

from .row_detection import _runs


def detect_missing_vines(mask: np.ndarray, row_info: dict, sensitivity: float = 1.5) -> list[dict]:
    if not row_info.get("available"):
        return []
    height, width = mask.shape
    radians = np.deg2rad(row_info["angle_degrees"])
    cosine, sine = np.float32(np.cos(radians)), np.float32(np.sin(radians))
    corner_along = [cosine * x + sine * y for x in (0, width - 1) for y in (0, height - 1)]
    offset = float(np.floor(min(corner_along)))
    positions = np.arange(offset, np.ceil(max(corner_along)) + 1, dtype=np.float32)[None, :]
    mask_u8 = mask.astype(np.uint8)
    candidates = []
    for row in row_info["rows"]:
        half_width = row["width"] * 0.55
        # Sampling only a narrow strip avoids full-frame coordinate grids at high
        # resolution. Pixels outside the actual image never count as bare ground.
        normals = np.arange(row["normal_center"] - half_width,
                            row["normal_center"] + half_width + 1, dtype=np.float32)[:, None]
        map_x = cosine * positions - sine * normals
        map_y = sine * positions + cosine * normals
        sampled = cv2.remap(mask_u8, map_x, map_y, cv2.INTER_NEAREST,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        if np.count_nonzero(sampled) < 100:
            continue
        valid = (map_x >= -0.5) & (map_x < width - 0.5) & (map_y >= -0.5) & (map_y < height - 0.5)
        support = valid.sum(axis=0)
        counts = sampled.sum(axis=0)
        fraction = counts / np.maximum(support, 1)
        fraction = cv2.GaussianBlur(fraction.astype(np.float32).reshape(1, -1), (0, 0), 1.5).ravel()
        populated = fraction > max(0.12, float(fraction.max()) * 0.28)
        components = [(a, b) for a, b in _runs(populated) if b - a >= max(3, row["width"] * 0.20)]
        if len(components) < 2:
            continue
        segment_sizes = np.array([b - a for a, b in components], dtype=float)
        interior = [(components[i][1], components[i + 1][0]) for i in range(len(components) - 1)]
        lengths = np.array([b - a for a, b in interior], dtype=float)
        # A gap must exceed canopy width and, with >=3 gaps, the ordinary vine spacing.
        ordinary = float(np.percentile(lengths, 35)) if len(lengths) >= 3 else 0.0
        minimum_gap = max(row["width"] * 0.80,
                          max(8.0, row["width"] * 0.85,
                              min(float(np.median(segment_sizes)), row["width"] * 1.5) * 0.70,
                              ordinary * 2.0) / sensitivity)
        for a, b in interior:
            if b - a < minimum_gap:
                continue
            # Both neighbours must show substantial canopy; never flag the row ends.
            t1, t2 = a + offset, b + offset
            n1, n2 = row["normal_center"] - half_width, row["normal_center"] + half_width
            corners = [(cosine * t - sine * n, sine * t + cosine * n) for t in (t1, t2) for n in (n1, n2)]
            x1 = max(0, int(np.floor(min(p[0] for p in corners))))
            x2 = min(width, int(np.ceil(max(p[0] for p in corners))))
            y1 = max(0, int(np.floor(min(p[1] for p in corners))))
            y2 = min(height, int(np.ceil(max(p[1] for p in corners))))
            if x2 <= x1 or y2 <= y1:
                continue
            t_center = (t1 + t2) / 2
            candidates.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2,
                               "center_x": float(cosine * t_center - sine * row["normal_center"]),
                               "center_y": float(sine * t_center + cosine * row["normal_center"]),
                               "row_id": row["row_id"], "gap_length_pixels": float(b - a),
                               "label": "Possible Canopy Gap"})
    return candidates
