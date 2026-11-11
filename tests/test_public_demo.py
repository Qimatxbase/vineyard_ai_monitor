"""The public entry point keeps filesystem discovery local and limits uploads."""
import io
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def button(app, label):
    return next(widget for widget in app.button if widget.label == label)


@pytest.fixture
def public_app(monkeypatch):
    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("VINEYARD_PUBLIC_DEMO", "1")
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    button(app, "Enter our project").click().run()
    assert not app.exception
    return app


def test_public_mode_blocks_folder_discovery_even_with_stale_selection(public_app):
    # Seed stale local state before the public source widget is constructed.
    public_app.session_state["source_choice"] = "Local folder"
    public_app.session_state["folder_images"] = ["/private/not-a-public-image.png"]
    public_app.session_state["scanned_folder"] = "/private"
    public_app.radio(key="workspace_page").set_value("Vineyard Analysis").run()

    assert not public_app.exception
    source = public_app.radio(key="source_choice")
    assert source.options == ["Upload images", "Synthetic demo"]
    assert source.value == "Upload images"
    assert not public_app.text_input
    assert not public_app.multiselect
    assert not any(widget.label == "Scan folder" for widget in public_app.button)
    assert button(public_app, "Analyse Vineyard").disabled


def test_public_entrypoint_runs_synthetic_analysis(monkeypatch):
    monkeypatch.chdir(ROOT)
    # Record the value before demo.py sets it so the local-mode suite is isolated.
    monkeypatch.setenv("VINEYARD_PUBLIC_DEMO", "1")
    app = AppTest.from_file(str(ROOT / "demo.py"), default_timeout=30).run()
    assert not app.exception
    button(app, "Enter our project").click().run()
    button(app, "Run synthetic analysis").click().run()

    assert not app.exception
    assert app.session_state["results"][0]["metadata"]["synthetic"] is True
    assert app.radio(key="source_choice").options == ["Upload images", "Synthetic demo"]
    assert any(widget.proto.label == "Complete result ZIP" for widget in app.get("download_button"))


def test_public_upload_limits_are_applied_before_analysis(public_app, monkeypatch):
    class UploadedImage(io.BytesIO):
        def __init__(self, name, payload):
            super().__init__(payload)
            self.name = name
            self.size = len(payload)

    class OversizedImage:
        name = "too-large.png"
        size = 10 * 1024 * 1024 + 1

        def getvalue(self):
            raise AssertionError("An oversized upload must not be read for analysis.")

    sample = (ROOT / "data/sample/synthetic_vineyard.png").read_bytes()
    uploaded = [OversizedImage()] + [UploadedImage(f"frame-{i}.png", sample) for i in range(1, 4)]
    # AppTest cannot fill file_uploader; replace only that input boundary.
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: uploaded)
    public_app.radio(key="workspace_page").set_value("Vineyard Analysis").run()
    button(public_app, "Analyse Vineyard").click().run()

    assert not public_app.exception
    assert any("too-large.png: exceeds the 10 MB input limit" in element.value for element in public_app.error)
    assert any("The first 3 images will be analysed" in element.value for element in public_app.warning)
    names = [result["metadata"]["source_name"] for result in public_app.session_state["results"]]
    assert names == ["frame-1.png", "frame-2.png"]
