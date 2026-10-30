"""Behavioural checks on controlled images; these are not real-vineyard accuracy claims."""
from dataclasses import replace

import cv2
import numpy as np
import pytest

from config import AnalysisConfig
from src.vision.canopy_segmentation import segment_canopy
from src.vision.pipeline import analyze_image
from src.vision.row_detection import detect_rows


def vineyard(gap=False, stress=False):
    image = np.full((480, 640, 3), (130, 95, 65), np.uint8)
    for y in (70, 155, 240, 325, 410):
        for x in range(45, 620, 38):
            if gap and y == 240 and 240 < x < 340:
                continue
            colour = (165, 155, 35) if stress and y == 155 and 300 < x < 500 else (45, 130, 45)
            cv2.ellipse(image, (x, y), (22, 14), 0, 0, 360, colour, -1)
    return image


def test_segmentation_finds_green_not_soil():
    image = np.full((100, 120, 3), (130, 95, 65), np.uint8)
    image[20:80, 20:100] = (35, 145, 35)
    mask = segment_canopy(image)
    assert mask.dtype == bool
    assert mask[30:70, 30:90].all()
    assert not mask[:15].any()
    assert abs(mask.mean() - 0.4) < 0.01


@pytest.mark.parametrize("mode", ["combined", "exg", "hsv", "otsu"])
def test_all_segmentation_modes_are_functional(mode):
    assert segment_canopy(vineyard(), replace(AnalysisConfig(), segmentation_mode=mode)).mean() > 0.15


def test_tiling_preserves_connected_components_across_seams():
    image = vineyard()
    whole = segment_canopy(image)
    tiled = segment_canopy(image, replace(AnalysisConfig(), tile_size=128))
    assert np.array_equal(whole, tiled)


def test_tiled_otsu_shares_global_threshold():
    image = np.random.default_rng(17).integers(0, 256, size=(257, 385, 3), dtype=np.uint8)
    config = replace(AnalysisConfig(), segmentation_mode="otsu", morphology_size=1, min_component_area=0)
    whole = segment_canopy(image, config)
    tiled = segment_canopy(image, replace(config, tile_size=128))
    assert np.array_equal(whole, tiled)


def test_small_components_removed():
    image = np.full((100, 100, 3), 100, np.uint8)
    image[10:12, 10:12] = (20, 160, 20)
    assert not segment_canopy(image).any()


def test_row_gap_is_interior_not_all_bare_soil():
    normal = analyze_image(vineyard())
    result = analyze_image(vineyard(gap=True))
    assert normal["row_info"]["available"]
    assert normal["gaps"] == []
    assert result["row_info"]["available"]
    assert len(result["gaps"]) == 1
    gap = result["gaps"][0]
    assert 240 < gap["center_x"] < 340
    assert abs(gap["center_y"] - 240) < 15
    assert gap["label"] == "Possible Canopy Gap"


def test_rotated_row_structure_and_gap():
    transform = cv2.getRotationMatrix2D((320, 240), 24, 1)
    image = cv2.warpAffine(vineyard(gap=True), transform, (640, 480), borderValue=(130, 95, 65))
    result = analyze_image(image)
    assert result["row_info"]["available"]
    assert abs(result["row_info"]["angle_degrees"] - 156) <= 4
    assert result["gaps"]
    assert all(0 <= g["x1"] < g["x2"] <= 640 and 0 <= g["y1"] < g["y2"] <= 480 for g in result["gaps"])


def test_no_vegetation_abstains_from_gap_and_stress():
    result = analyze_image(np.full((120, 160, 3), 128, np.uint8))
    assert not result["mask"].any()
    assert not result["row_info"]["available"]
    assert not result["gaps"]
    assert result["summary"]["anomaly_count"] == 0
    assert result["summary"]["low_growth_count"] == 0
    assert all(r["category"] != "GREEN" and not r["has_canopy"] for r in result["regions"])


def test_uniform_canopy_has_no_gap_evidence():
    mask = np.ones((160, 200), bool)
    assert not detect_rows(mask)["available"]


def test_unstructured_speckles_and_single_row_abstain():
    random = np.random.default_rng(6).random((180, 240)) < 0.3
    assert not detect_rows(random)["available"]
    image = np.full((480, 640, 3), (130, 95, 65), np.uint8)
    for x in range(40, 610, 55):
        cv2.ellipse(image, (x, 240), (15, 10), 0, 0, 360, (40, 140, 40), -1)
    assert not analyze_image(image)["row_info"]["available"]


def test_colour_anomaly_responds_to_yellowing():
    normal = analyze_image(vineyard())
    stressed = analyze_image(vineyard(stress=True))
    assert max(r["anomaly_score"] for r in normal["regions"]) < 0.2
    assert max(r["anomaly_score"] for r in stressed["regions"]) >= 0.55
    assert any("colour" in " ".join(r["issues"]) for r in stressed["regions"] if r["anomaly_score"] >= 0.55)


def test_resize_preserves_original_coordinate_mapping_and_json_types():
    result = analyze_image(vineyard(gap=True), replace(AnalysisConfig(), max_dimension=320), synthetic=True)
    assert result["image"].shape == (240, 320, 3)
    assert result["metadata"]["original_width"] == 640
    assert result["metadata"]["scale_x"] == 2
    assert result["metadata"]["synthetic"] is True
    for region in result["regions"]:
        assert region["original_x1"] == region["x1"] * 2
        assert region["original_y2"] == region["y2"] * 2
    import json
    json.dumps({k: v for k, v in result.items() if k not in {"image", "mask"}})


def test_thin_image_uses_shared_preprocessing_geometry():
    from src.data.preprocessing import prepare_image
    image = np.full((2, 1001, 3), 128, np.uint8)
    result = analyze_image(image, replace(AnalysisConfig(), max_dimension=64))
    resized, mapping = prepare_image(image, 64)
    assert result["image"].shape == resized.shape == (1, 64, 3)
    assert result["metadata"]["scale_y"] == mapping["scale_y"]
    assert not result["row_info"]["available"]
    assert result["regions"][-1]["original_y2"] == 2


@pytest.mark.parametrize("bad", [np.zeros((0, 0, 3), np.uint8), np.zeros((10, 10), np.uint8), np.zeros((10, 10, 3), float)])
def test_invalid_input_rejected(bad):
    with pytest.raises(ValueError):
        analyze_image(bad)
