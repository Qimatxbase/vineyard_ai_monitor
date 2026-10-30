"""Strict annotation loading and visual pixel error analysis."""
from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError

from .metrics import binary_mask, segmentation_metrics, validate_boxes


def load_ground_truth_mask(source, expected_shape: tuple[int, int] | None = None) -> np.ndarray:
    """Read a binary grayscale image; reject RGB/palette pseudo-colour imagery.

    Coordinates and dimensions must already align. No EXIF transforms, resizing,
    colour conversion, or intensity thresholding is performed on annotations.
    """
    if isinstance(source, np.ndarray):
        array = source
    else:
        if isinstance(source, (bytes, bytearray)):
            source = BytesIO(source)
        try:
            if hasattr(source, "seek"):
                source.seek(0)
            with Image.open(source) as image:
                if image.mode not in {"1", "L", "I", "I;16", "I;16B", "I;16L", "F"}:
                    raise ValueError("Ground truth must be a binary grayscale image. RGB or palette "
                                     "pseudo-coloured reference images are not accepted as masks.")
                if image.width * image.height > 40_000_000:
                    raise ValueError("Ground-truth image exceeds the 40 megapixel limit.")
                array = np.array(image)
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError("Could not read ground-truth image; use a binary grayscale PNG or TIFF.") from exc
    mask = binary_mask(array, name="Ground truth")
    if expected_shape is not None and mask.shape != tuple(expected_shape):
        raise ValueError(f"Ground truth shape {mask.shape} does not match required shape {tuple(expected_shape)}. "
                         "Annotations must refer to the same image, crop, and resolution.")
    return mask


def load_boxes_json(source) -> list[list[float]]:
    """Read JSON list of xyxy boxes or {\"boxes\": [...]} without inference."""
    try:
        if hasattr(source, "read"):
            if hasattr(source, "seek"):
                source.seek(0)
            raw = source.read()
        elif isinstance(source, Path):
            raw = source.read_bytes()
        elif isinstance(source, str) and not source.lstrip().startswith(("[", "{")):
            raw = Path(source).read_bytes()
        else:
            raw = source
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8-sig")
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Could not read box annotations. Supply valid UTF-8 JSON with a list of xyxy boxes.") from exc
    if isinstance(data, dict):
        if "boxes" not in data:
            raise ValueError("Annotation object must contain a 'boxes' list.")
        data = data["boxes"]
    return validate_boxes(data)


def confusion_overlay(pred_mask: np.ndarray, gt_mask: np.ndarray) -> np.ndarray:
    """RGB image: green TP, red FP, blue FN, light grey TN."""
    pred, truth = binary_mask(pred_mask), binary_mask(gt_mask)
    if pred.shape != truth.shape:
        raise ValueError("Prediction and ground-truth shapes must match exactly.")
    output = np.full((*pred.shape, 3), (226, 231, 224), dtype=np.uint8)
    output[pred & truth] = (39, 145, 90)
    output[pred & ~truth] = (220, 65, 65)
    output[~pred & truth] = (55, 116, 215)
    return output


def evaluate_segmentation(pred_mask: np.ndarray, gt_mask: np.ndarray) -> dict:
    """Return {metrics: dict, confusion: uint8 RGB array}; no synthetic scores."""
    metrics = segmentation_metrics(pred_mask, gt_mask)
    return {"metrics": metrics, "confusion": confusion_overlay(pred_mask, gt_mask)}
