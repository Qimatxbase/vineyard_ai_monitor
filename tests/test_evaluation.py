from io import BytesIO

import numpy as np
from PIL import Image
import pytest

from src.evaluation.evaluate import (confusion_overlay, evaluate_segmentation,
                                     load_boxes_json, load_ground_truth_mask)
from src.evaluation.metrics import detection_metrics, segmentation_metrics


def image_bytes(array, mode=None):
    buffer = BytesIO()
    Image.fromarray(array, mode=mode).save(buffer, format="PNG")
    return buffer.getvalue()


def test_segmentation_hand_computed():
    pred = np.array([[1, 1], [0, 0]], bool)
    truth = np.array([[1, 0], [1, 0]], bool)
    metrics = segmentation_metrics(pred, truth)
    assert (metrics["tp"], metrics["fp"], metrics["fn"], metrics["tn"]) == (1, 1, 1, 1)
    assert metrics["intersection_over_union"] == pytest.approx(1 / 3)
    assert metrics["dice"] == metrics["precision"] == metrics["recall"] == 0.5


def test_empty_foreground_convention():
    empty = np.zeros((3, 3), bool)
    assert segmentation_metrics(empty, empty)["dice"] == 1.0
    assert detection_metrics([], [])["f1"] == 1.0
    assert detection_metrics([], [[0, 0, 2, 2]])["f1"] == 0.0
    assert detection_metrics([[0, 0, 2, 2]], [])["precision"] == 0.0


def test_shape_mismatch_and_probability_rejected():
    with pytest.raises(ValueError, match="shape mismatch"):
        segmentation_metrics(np.zeros((3, 3)), np.zeros((4, 3)))
    with pytest.raises(ValueError, match="binary values"):
        segmentation_metrics(np.array([[0.5]]), np.array([[1]]))


def test_confusion_colours_and_wrapper():
    pred = np.array([[1, 1], [0, 0]], bool)
    truth = np.array([[1, 0], [1, 0]], bool)
    result = evaluate_segmentation(pred, truth)
    image = result["confusion"]
    assert tuple(image[0, 0]) == (39, 145, 90)
    assert tuple(image[0, 1]) == (220, 65, 65)
    assert tuple(image[1, 0]) == (55, 116, 215)
    assert image.dtype == np.uint8


def test_detection_no_duplicate_true_positives():
    result = detection_metrics([[0, 0, 10, 10], [0, 0, 10, 10]], [[0, 0, 10, 10]])
    assert (result["tp"], result["fp"], result["fn"]) == (1, 1, 0)
    assert result["precision"] == 0.5


def test_matching_avoids_greedy_loss():
    # First prediction overlaps both annotations; second overlaps only first.
    result = detection_metrics([[0, 0, 15, 10], [0, 0, 10, 10]],
                               [[0, 0, 10, 10], [5, 0, 15, 10]], iou_threshold=0.5)
    assert result["tp"] == 2
    assert len({match["ground_truth_index"] for match in result["matches"]}) == 2


@pytest.mark.parametrize("boxes", [ [[0, 0, 0, 2]], [[0, 0, float("nan"), 2]],
                                  [[-1, 0, 2, 2]], [[0, 0, 2]], [[False, 0, 2, 2]] ])
def test_invalid_boxes(boxes):
    with pytest.raises(ValueError):
        detection_metrics(boxes, [])


def test_box_loader_formats():
    assert load_boxes_json(b'{"boxes":[[1,2,4,6]]}') == [[1.0, 2.0, 4.0, 6.0]]
    assert load_boxes_json('[{"x1":1,"y1":2,"x2":4,"y2":6}]') == [[1, 2, 4, 6]]
    assert load_boxes_json("[]") == []
    with pytest.raises(ValueError):
        load_boxes_json('{"detections":[]}')


def test_strict_mask_loading_and_shape():
    source = image_bytes(np.array([[0, 255], [255, 0]], np.uint8))
    assert load_ground_truth_mask(source, (2, 2)).sum() == 2
    with pytest.raises(ValueError, match="does not match"):
        load_ground_truth_mask(source, (3, 3))


def test_reject_coloured_reference_and_nonbinary_greyscale():
    with pytest.raises(ValueError, match="pseudo-coloured"):
        load_ground_truth_mask(image_bytes(np.zeros((2, 2, 3), np.uint8)))
    with pytest.raises(ValueError, match="binary values"):
        load_ground_truth_mask(image_bytes(np.array([[0, 100]], np.uint8)))

