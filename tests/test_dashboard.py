"""Streamlit UI smoke checks; generated-demo scores are never field evidence."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def app(monkeypatch):
    monkeypatch.chdir(ROOT)
    instance = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not instance.exception
    return instance


def button(app, label):
    return next(widget for widget in app.button if widget.label == label)


def toggle(app, label):
    return next(widget for widget in app.toggle if widget.label == label)


def route(app, page):
    app.radio(key="workspace_page").set_value(page).run()
    assert not app.exception


def download_keys(app):
    return {widget.key for widget in app.get("download_button")}


def test_complete_synthetic_demo_map_evaluation_and_about(app):
    assert app.radio(key="workspace_page").value == "Overview"
    assert any("SYNTHETIC" in element.value for element in app.caption)
    assert len(app.get("plotly_chart")) == 1

    button(app, "Try the synthetic vineyard demo →").click().run()
    assert not app.exception
    assert app.radio(key="workspace_page").value == "Vineyard Analysis"
    result = app.session_state["results"][0]
    assert result["metadata"]["synthetic"] is True
    assert result["mask"].shape == result["image"].shape[:2]
    assert result["regions"]
    assert any("SYNTHETIC DEMO" in warning.value for warning in app.warning)
    assert any(widget.proto.label == "Complete result ZIP" for widget in app.get("download_button"))

    route(app, "Vineyard Health Map")
    assert len(app.get("plotly_chart")) == 3
    toggle(app, "Canopy overlay").set_value(True).run()
    toggle(app, "Possible gap markers").set_value(False).run()
    toggle(app, "Region colours").set_value(False).run()
    assert not app.exception
    assert toggle(app, "Canopy overlay").value is True
    assert toggle(app, "Possible gap markers").value is False
    region_widget = next(widget for widget in app.selectbox if widget.label == "Region")
    region_widget.select(region_widget.options[-1]).run()
    assert not app.exception

    route(app, "Evaluation")
    # Running the pipeline alone must never produce invented validation scores.
    assert not app.metric
    assert any("No canopy ground truth supplied" in element.value for element in app.caption)
    assert any("No gap ground truth supplied" in element.value for element in app.caption)
    assert any("No suitable anomaly ground truth supplied" in element.value for element in app.caption)
    toggle(app, "Use synthetic demonstration annotations").set_value(True).run()
    assert any("do not establish real vineyard accuracy" in warning.value for warning in app.warning)

    for label, expected_key in [
        ("Evaluate canopy segmentation", "download_eval_canopy"),
        ("Evaluate possible gaps", "download_eval_canopy_gaps"),
        ("Evaluate visual anomalies", "download_eval_visual_anomaly"),
    ]:
        button(app, label).click().run()
        assert not app.exception
        assert not app.error
        assert app.metric
        assert expected_key in download_keys(app)
        # Results remain available after a regular rerun/download interaction.
        app.run()
        assert expected_key in download_keys(app)

    toggle(app, "Use synthetic demonstration annotations").set_value(False).run()
    assert not app.metric
    assert not download_keys(app)

    route(app, "About the Project")
    assert app.title[0].value == "About Vineyard AI Monitor"
    assert any("No GPS positions" in element.value for element in app.markdown)
    assert len(app.table) == 1


def test_local_folder_relative_path_and_bundled_sample(app):
    route(app, "Vineyard Analysis")
    app.radio(key="source_choice").set_value("Local folder").run()
    app.text_input[0].set_value("data/sample").run()
    button(app, "Scan folder").click().run()
    assert not app.exception and not app.error
    vineyard = str((ROOT / "data" / "sample" / "synthetic_vineyard.png").resolve())
    app.multiselect[0].set_value([vineyard]).run()
    button(app, "Analyse Vineyard").click().run()
    assert not app.exception and not app.error
    result = app.session_state["results"][0]
    assert result["metadata"]["source_name"] == "synthetic_vineyard.png"
    assert result["metadata"]["original_width"] == 960
    assert result["metadata"]["original_height"] == 640
    assert result["regions"]
    # A local copy of the bundled demonstration must retain truthful provenance.
    assert result["metadata"]["synthetic"] is True
    assert any("SYNTHETIC DEMO" in warning.value for warning in app.warning)


def test_missing_local_folder_shows_actionable_error(app, tmp_path):
    route(app, "Vineyard Analysis")
    app.radio(key="source_choice").set_value("Local folder").run()
    app.text_input[0].set_value(str(tmp_path / "no_such_vineyard")).run()
    button(app, "Scan folder").click().run()
    assert not app.exception
    assert any("Image folder does not exist" in error.value for error in app.error)
    assert button(app, "Analyse Vineyard").disabled


def test_evaluation_without_analysis_invites_demo_without_scores(app):
    route(app, "Evaluation")
    assert not app.metric
    assert any("Run an analysis" in element.value for element in app.info)
    assert button(app, "Open synthetic demo")
    assert not app.get("download_button")

