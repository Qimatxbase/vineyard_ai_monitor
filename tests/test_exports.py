"""Exports preserve real values, provenance, and explicit image coordinate frames."""
from copy import deepcopy
from io import BytesIO
import json
import zipfile

import numpy as np
import pandas as pd
from PIL import Image
import pytest

from config import AnalysisConfig
from src.mapping.health_map import create_health_map
from src.mapping.visualization import annotated_image, health_map_png
from src.utils.export import (batch_bundle, export_bundle, original_mask_png,
                              regions_csv, result_json)
from src.vision.pipeline import analyze_image


@pytest.fixture
def analysis():
    image = np.full((64, 96, 3), (128, 105, 79), np.uint8)
    image[8:26, 5:90] = (40, 155, 55)
    result = analyze_image(image, AnalysisConfig(grid_rows=2, grid_cols=3,
                           morphology_size=1, min_component_area=0),
                           source_name="synthetic_demo.png", synthetic=True)
    # Exercise different original and processed frames independently of resizing.
    result["metadata"].update(original_width=192, original_height=128,
                              scale_x=2.0, scale_y=2.0)
    for region in result["regions"]:
        for key in ("x1", "y1", "x2", "y2"):
            region["original_" + key] = region[key] * 2
    # A known candidate allows meaningful rendering/export checks even though a
    # single broad row is intentionally insufficient evidence for row detection.
    result["gaps"] = [{"x1": 30, "y1": 10, "x2": 42, "y2": 25,
                        "center_x": 36, "center_y": 17.5,
                        "original_x1": 60, "original_y1": 20,
                        "original_x2": 84, "original_y2": 50,
                        "label": "Possible Canopy Gap"}]
    result["summary"]["gap_count"] = 1
    result["regions"][0].update(category="RED", anomaly_score=0.72,
                               issues=["Visual Anomaly"], has_canopy=True)
    return result


def test_pipeline_maps_full_extent_and_all_region_coordinates():
    image = np.full((180, 310, 3), (40, 150, 50), np.uint8)
    result = analyze_image(image, AnalysisConfig(max_dimension=128,
                           grid_rows=3, grid_cols=4), source_name="actual_input.png")
    metadata = result["metadata"]
    assert metadata["original_width"] == 310
    assert metadata["original_height"] == 180
    assert metadata["processed_width"] == 128
    assert max(r["original_x2"] for r in result["regions"]) == 310
    assert max(r["original_y2"] for r in result["regions"]) == 180
    for region in result["regions"]:
        for field, scale in (("x1", metadata["scale_x"]), ("x2", metadata["scale_x"]),
                             ("y1", metadata["scale_y"]), ("y2", metadata["scale_y"])):
            assert region["original_" + field] == round(region[field] * scale)


def test_json_preserves_results_and_provenance(analysis):
    document = json.loads(result_json(analysis))
    assert "image" not in document and "mask" not in document
    assert document["metadata"]["synthetic"] is True
    assert document["summary"] == analysis["summary"]
    assert document["config"] == analysis["config"]
    assert document["regions"][0]["anomaly_score"] == 0.72
    assert document["gaps"][0]["original_x2"] == 84
    assert "processed pixels" in document["coordinates"]
    assert "not disease diagnosis" in document["interpretation"]


def test_json_numpy_and_nonfinite_values(analysis):
    analysis["summary"]["extra"] = np.float64(float("nan"))
    analysis["row_info"]["extra_array"] = np.array([1, 2])
    document = json.loads(result_json(analysis))
    assert document["summary"]["extra"] is None
    assert document["row_info"]["extra_array"] == [1, 2]


def test_csv_contains_matching_values_and_source(analysis):
    frame = pd.read_csv(BytesIO(regions_csv(analysis)))
    assert len(frame) == len(analysis["regions"])
    assert frame["source_name"].eq("synthetic_demo.png").all()
    assert frame["synthetic"].all()
    assert frame.iloc[0]["anomaly_score"] == 0.72
    assert frame.iloc[0]["issues"] == "Visual Anomaly"
    assert frame.iloc[-1]["original_x2"] == 192


def test_mask_png_original_size_and_binary_values(analysis):
    with Image.open(BytesIO(original_mask_png(analysis))) as image:
        assert image.size == (192, 128)
        actual = np.array(image)
        assert set(np.unique(actual)) == {0, 255}
        assert np.array_equal(actual[::2, ::2] > 0, analysis["mask"])


def test_bundle_contains_actual_pngs_and_json(analysis):
    with zipfile.ZipFile(BytesIO(export_bundle(analysis))) as archive:
        assert set(archive.namelist()) == {
            "analysis.json", "regions.csv", "canopy_mask.png", "annotated.png", "health_map.png"}
        assert json.loads(archive.read("analysis.json"))["metadata"]["synthetic"]
        with Image.open(BytesIO(archive.read("annotated.png"))) as image:
            assert image.size == (96, 64)
            assert np.array(image).shape == analysis["image"].shape
            assert not np.array_equal(np.array(image), analysis["image"])
        with Image.open(BytesIO(archive.read("health_map.png"))) as image:
            assert image.height == 64 + 98
            assert image.width >= 660


def test_batch_unique_sanitized_names_and_summary(analysis):
    other = deepcopy(analysis)
    analysis["metadata"]["source_name"] = "../../same vineyard.png"
    other["metadata"]["source_name"] = "../../same vineyard.png"
    with zipfile.ZipFile(BytesIO(batch_bundle([analysis, other]))) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)) == 3
        assert not any("/" in name or ".." in name for name in names)
        assert names[0].startswith("01_") and names[1].startswith("02_")
        summary = pd.read_csv(BytesIO(archive.read("batch_summary.csv")))
        assert len(summary) == 2
        assert summary["synthetic"].all()
        assert summary["gap_count"].tolist() == [1, 1]
        for name in names[:2]:
            with zipfile.ZipFile(BytesIO(archive.read(name))) as inner:
                assert "canopy_mask.png" in inner.namelist()


def test_map_image_frame_hover_provenance_and_gap_toggle(analysis):
    figure = create_health_map(analysis)
    assert tuple(figure.layout.xaxis.range) == (0, 96)
    assert tuple(figure.layout.yaxis.range) == (64, 0)
    assert figure.layout.yaxis.scaleanchor == "x"
    assert len(figure.layout.images) == 1
    assert len(figure.layout.shapes) == len(analysis["regions"])
    assert any(trace.name == "Possible canopy gap" for trace in figure.data)
    assert "Original pixel top-left" in figure.data[0].hovertemplate
    no_gaps = create_health_map(analysis, show_gaps=False)
    assert all(trace.name != "Possible canopy gap" for trace in no_gaps.data)


def test_segmentation_toggle_changes_base_image(analysis):
    normal = create_health_map(analysis, show_segmentation=False)
    segmented = create_health_map(analysis, show_segmentation=True)
    assert normal.layout.images[0].source != segmented.layout.images[0].source


def test_anomaly_toggle_changes_overlay_strength(analysis):
    regular = create_health_map(analysis, show_anomalies=False)
    anomalous = create_health_map(analysis, show_anomalies=True)
    region = analysis["regions"][0]
    regular_shape = next(s for s in regular.layout.shapes if s.x0 == region["x1"] and s.y0 == region["y1"])
    anomalous_shape = next(s for s in anomalous.layout.shapes if s.x0 == region["x1"] and s.y0 == region["y1"])
    assert regular_shape.fillcolor != anomalous_shape.fillcolor

