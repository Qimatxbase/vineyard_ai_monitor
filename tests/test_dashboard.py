"""Streamlit UI smoke checks; generated-demo scores are never field evidence."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def welcome_app(monkeypatch):
    monkeypatch.chdir(ROOT)
    instance = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not instance.exception
    return instance


@pytest.fixture
def app(welcome_app):
    button(welcome_app, "Enter our project").click().run()
    assert not welcome_app.exception
    return welcome_app


def button(app, label):
    return next(widget for widget in app.button if widget.label == label)


def toggle(app, label):
    return next(widget for widget in app.toggle if widget.label == label)


def route(app, page):
    app.radio(key="workspace_page").set_value(page).run()
    assert not app.exception


def download_keys(app):
    return {widget.key for widget in app.get("download_button")}


def test_welcome_introduces_project_before_dashboard(welcome_app):
    copy = "\n".join(
        element.value
        for elements in (welcome_app.markdown, welcome_app.title, welcome_app.header, welcome_app.subheader)
        for element in elements
    )
    assert "Who we are" in copy
    assert "What we solve" in copy
    assert button(welcome_app, "Enter our project")
    assert not welcome_app.radio
    assert not welcome_app.text_input
    assert not welcome_app.metric
    assert not welcome_app.get("plotly_chart")

    button(welcome_app, "Enter our project").click().run()
    assert not welcome_app.exception
    assert welcome_app.session_state["workspace_entered"] is True
    assert welcome_app.radio(key="workspace_page").value == "Dashboard"


def test_return_to_overview_preserves_analysis_and_drone_state(app):
    button(app, "Run synthetic analysis").click().run()
    result = app.session_state["results"][0]
    route(app, "Drone Connect")
    button(app, "Discover demo drone").click().run()
    button(app, "Connect demo drone").click().run()
    drone_state = app.session_state["drone_demo"].copy()

    route(app, "Overview")
    assert not app.exception
    assert app.session_state["workspace_entered"] is False
    assert not app.radio
    assert button(app, "Enter our project")
    assert app.session_state["results"][0]["summary"] == result["summary"]
    assert app.session_state["drone_demo"] == drone_state

    button(app, "Enter our project").click().run()
    assert not app.exception
    assert app.radio(key="workspace_page").value == "Dashboard"
    assert any(f"Source: {result['metadata']['source_name']}" in element.value for element in app.caption)
    route(app, "Drone Connect")
    assert app.session_state["drone_demo"] == drone_state
    assert not button(app, "Disconnect").disabled


def test_complete_synthetic_demo_map_and_evaluation(app):
    navigation = app.radio(key="workspace_page")
    assert navigation.value == "Dashboard"
    assert navigation.options == ["Overview", "Dashboard", "Analysis", "Health map", "Drone connect", "Evaluation"]
    assert not app.sidebar.radio
    assert any("SYNTHETIC" in element.value for element in app.caption)
    assert app.metric
    assert app.get("plotly_chart")

    button(app, "Run synthetic analysis").click().run()
    assert not app.exception
    assert app.radio(key="workspace_page").value == "Vineyard Analysis"
    result = app.session_state["results"][0]
    assert result["metadata"]["synthetic"] is True
    assert result["mask"].shape == result["image"].shape[:2]
    assert result["regions"]
    assert any("SYNTHETIC DEMO" in warning.value for warning in app.warning)
    assert any(widget.proto.label == "Complete result ZIP" for widget in app.get("download_button"))

    route(app, "Dashboard")
    assert any(f"Source: {result['metadata']['source_name']}" in element.value for element in app.caption)
    canopy = next(widget for widget in app.metric if widget.label == "Visible canopy")
    assert canopy.value == f"{result['summary']['canopy_coverage']:.1f}%"
    button(app, "Open health map").click().run()
    assert not app.exception
    assert app.radio(key="workspace_page").value == "Vineyard Health Map"
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


def test_drone_demo_capture_reaches_map_and_survives_disconnect(app):
    route(app, "Drone Connect")
    assert any("DEMO MODE" in element.value for element in app.caption)
    assert button(app, "Connect demo drone").disabled
    assert button(app, "Capture demo frame").disabled
    button(app, "Discover demo drone").click().run()
    button(app, "Connect demo drone").click().run()
    assert not app.exception and not app.error
    assert app.session_state["drone_demo"]["status"] == "ready"
    assert button(app, "Start demo inspection").disabled

    button(app, "Run preflight check").click().run()
    button(app, "Start demo inspection").click().run()
    button(app, "Advance inspection").click().run()
    button(app, "Capture demo frame").click().run()
    assert not app.exception and not app.error
    state = app.session_state["drone_demo"]
    assert state["status"] == "inspecting"
    assert state["waypoint_index"] == 1
    assert state["captured_frames"] == 1
    result = app.session_state["results"][0]
    assert result["metadata"]["synthetic"] is True
    assert result["metadata"]["source_name"] == "Drone demo · generated vineyard frame"
    assert result["regions"] and result["mask"].any()

    button(app, "Open captured health map").click().run()
    assert not app.exception
    assert app.radio(key="workspace_page").value == "Vineyard Health Map"
    assert any("SYNTHETIC DEMO" in element.value for element in app.warning)
    assert any(widget.proto.label == "Complete result ZIP" for widget in app.get("download_button"))

    route(app, "Drone Connect")
    button(app, "Disconnect").click().run()
    assert not app.exception
    assert app.session_state["drone_demo"]["status"] == "disconnected"
    assert app.session_state["drone_demo"]["captured_frames"] == 1
    assert app.session_state["results"][0]["summary"] == result["summary"]
    assert button(app, "Capture demo frame").disabled


@pytest.mark.parametrize("scenario", ["Low battery", "Weak signal"])
def test_failed_demo_preflight_blocks_inspection(app, scenario):
    route(app, "Drone Connect")
    button(app, "Discover demo drone").click().run()
    app.selectbox(key="drone_scenario").set_value(scenario).run()
    button(app, "Connect demo drone").click().run()
    button(app, "Run preflight check").click().run()
    assert not app.exception and not app.error
    assert app.session_state["drone_demo"]["preflight_checked"]
    assert button(app, "Start demo inspection").disabled
    assert button(app, "Capture demo frame").disabled
    assert any("Inspection blocked" in element.value for element in app.warning)

