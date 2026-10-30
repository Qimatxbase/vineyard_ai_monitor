"""Deterministic drawn vineyard fixture, never presented as real-world validation."""
from __future__ import annotations

import cv2
import numpy as np


def generate_demo(seed: int = 7) -> dict:
    """Return synthetic RGB, canopy/anomaly masks and deliberate gap boxes.

    Shapes and colours are fabricated. Exact drawn-shape masks support software
    checks only; their scores do not estimate field performance.
    """
    rng = np.random.default_rng(seed)
    height, width = 640, 960
    y_grid, x_grid = np.mgrid[:height, :width]
    soil = np.array([150, 123, 91], dtype=np.float32)
    illumination = 7 * np.sin(x_grid / 130) + 4 * np.cos(y_grid / 70)
    noise = rng.normal(0, 4, (height, width, 1))
    image = np.clip(soil + illumination[..., None] + noise, 0, 255).astype(np.uint8)
    canopy = np.zeros((height, width), np.uint8)
    anomaly = np.zeros_like(canopy)
    gap_boxes = [[330, 132, 435, 177], [570, 372, 715, 417]]
    for row, y in enumerate(range(75, 600, 80)):
        # Faint parallel tractor tracks provide visual context, not segmentation labels.
        cv2.line(image, (20, y + 30), (940, y + 30), (143, 116, 84), 3)
        for x in range(55, 920, 40):
            if (row == 1 and 335 <= x <= 415) or (row == 4 and 575 <= x <= 695):
                continue
            rx, ry = int(rng.integers(22, 29)), int(rng.integers(14, 20))
            if row in {5, 6} and 90 <= x <= 290:
                rx, ry = 15, 9  # Deliberate low-density patch.
            cx, cy = x + int(rng.integers(-4, 5)), y + int(rng.integers(-3, 4))
            shape = np.zeros_like(canopy)
            cv2.ellipse(shape, (cx, cy), (rx, ry), int(rng.integers(-15, 16)), 0, 360, 255, -1)
            selected = shape > 0
            stressed = row in {2, 3} and 615 <= x <= 815
            color = np.array([168, 158, 48] if stressed else [45, 110, 52], dtype=np.float32)
            texture = rng.normal(0, 9, (int(selected.sum()), 1))
            image[selected] = np.clip(color + texture, 0, 255).astype(np.uint8)
            canopy[selected] = 255
            if stressed:
                anomaly[selected] = 255
    return {"image": image, "canopy_mask": canopy.astype(bool), "gap_boxes": gap_boxes,
            "anomaly_mask": anomaly.astype(bool),
            "metadata": {"synthetic": True, "seed": int(seed), "source_name": "Synthetic vineyard demonstration",
                         "description": "Drawn RGB vineyard with deliberately removed canopy and yellow canopy. Software demonstration only."}}
