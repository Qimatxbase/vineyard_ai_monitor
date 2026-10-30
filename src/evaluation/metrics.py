"""Evaluation against explicitly supplied, independent binary annotations.

All-negative convention: two empty foreground masks/box sets score 1.0.
Precision is zero when predictions are empty but annotations are not. Recall is
1.0 when annotations are empty; false-positive predictions still lower precision
and F1. Undefined ratios never become NaN.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import math

import numpy as np


def binary_mask(mask: np.ndarray, *, name: str = "mask") -> np.ndarray:
    """Validate a nonempty 2-D binary array without thresholding probabilities."""
    array = np.asarray(mask)
    if array.ndim != 2 or array.size == 0:
        raise ValueError(f"{name} must be a nonempty two-dimensional binary mask.")
    if not np.isin(array, [0, 1, 255]).all():
        raise ValueError(f"{name} must contain only binary values 0, 1, or 255.")
    return array != 0


def _classification_counts(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if tp + fp else float(fn == 0)
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 1.0
    return {"precision": precision, "recall": recall, "f1": f1,
            "tp": tp, "fp": fp, "fn": fn}


def segmentation_metrics(pred_mask: np.ndarray, gt_mask: np.ndarray) -> dict:
    """Pixel metrics; shapes must match exactly and are never resized here."""
    pred = binary_mask(pred_mask, name="Prediction")
    truth = binary_mask(gt_mask, name="Ground truth")
    if pred.shape != truth.shape:
        raise ValueError(f"Mask shape mismatch: prediction {pred.shape}, ground truth {truth.shape}. "
                         "Supply an annotation aligned to this exact image and resolution.")
    tp = int(np.count_nonzero(pred & truth))
    fp = int(np.count_nonzero(pred & ~truth))
    fn = int(np.count_nonzero(~pred & truth))
    tn = int(np.count_nonzero(~pred & ~truth))
    union = tp + fp + fn
    result = _classification_counts(tp, fp, fn)
    result.update(intersection_over_union=tp / union if union else 1.0,
                  dice=result["f1"], tn=tn)
    return result


def validate_boxes(boxes: Sequence) -> list[list[float]]:
    """Validate half-open pixel boxes [x1,y1,x2,y2] with positive area."""
    if not isinstance(boxes, (list, tuple, np.ndarray)):
        raise ValueError("Boxes must be a list of [x1, y1, x2, y2] coordinates.")
    result = []
    for index, box in enumerate(boxes):
        if isinstance(box, Mapping):
            try:
                box = [box[k] for k in ("x1", "y1", "x2", "y2")]
            except KeyError as exc:
                raise ValueError(f"Box {index} requires x1, y1, x2, y2.") from exc
        try:
            if len(box) != 4 or any(isinstance(value, (bool, np.bool_)) for value in box):
                raise ValueError
            coords = [float(value) for value in box]
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Box {index} must contain four finite numeric coordinates.") from exc
        if not all(math.isfinite(value) for value in coords):
            raise ValueError(f"Box {index} contains a non-finite coordinate.")
        x1, y1, x2, y2 = coords
        if min(x1, y1) < 0 or x2 <= x1 or y2 <= y1:
            raise ValueError(f"Box {index} requires nonnegative origins and positive width/height.")
        result.append(coords)
    return result


def box_iou(first: Sequence[float], second: Sequence[float]) -> float:
    """Intersection over union for validated xyxy boxes."""
    ax1, ay1, ax2, ay2 = first
    bx1, by1, bx2, by2 = second
    intersection = max(0.0, min(ax2, bx2) - max(ax1, bx1)) * max(0.0, min(ay2, by2) - max(ay1, by1))
    union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - intersection
    return intersection / union if union else 0.0


def detection_metrics(pred_boxes: Sequence, gt_boxes: Sequence, iou_threshold: float = 0.5) -> dict:
    """Object metrics using deterministic one-to-one maximum-cardinality matching.

    Each eligible edge must meet IoU >= threshold. Highest-IoU edges are tried
    first, then augmenting paths resolve overlaps so a greedy choice cannot
    needlessly lower recall. No annotation can be counted twice.
    """
    if not math.isfinite(iou_threshold) or not 0 < iou_threshold <= 1:
        raise ValueError("IoU threshold must be greater than zero and at most one.")
    predictions, annotations = validate_boxes(pred_boxes), validate_boxes(gt_boxes)
    scores = [[box_iou(pred, truth) for truth in annotations] for pred in predictions]
    edges = [sorted((j for j, score in enumerate(row) if score >= iou_threshold),
                    key=lambda j: (-row[j], j)) for row in scores]
    matched: dict[int, int] = {}

    def augment(prediction: int, seen: set[int]) -> bool:
        for annotation in edges[prediction]:
            if annotation in seen:
                continue
            seen.add(annotation)
            if annotation not in matched or augment(matched[annotation], seen):
                matched[annotation] = prediction
                return True
        return False

    # Prefer predictions with fewer eligible targets; augmenting paths still
    # guarantee maximum cardinality regardless of this deterministic order.
    for index in sorted(range(len(predictions)), key=lambda i: (len(edges[i]), i)):
        augment(index, set())
    tp = len(matched)
    result = _classification_counts(tp, len(predictions) - tp, len(annotations) - tp)
    result["iou_threshold"] = float(iou_threshold)
    result["matches"] = [{"prediction_index": p, "ground_truth_index": g,
                           "iou": scores[p][g]} for g, p in sorted(matched.items())]
    return result
