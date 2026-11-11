"""Cached analysis entry points; the vision pipeline stays independent of UI."""
import hashlib
from pathlib import Path

import streamlit as st

from config import AnalysisConfig
from src.data.dataset_loader import load_image
from src.data.synthetic import generate_demo
from src.vision.pipeline import analyze_image


@st.cache_data(show_spinner=False)
def _bundled_demo_digest():
    fixture = Path(__file__).resolve().parents[2] / "data" / "sample" / "synthetic_vineyard.png"
    return hashlib.sha256(fixture.read_bytes()).digest() if fixture.is_file() else None


def is_bundled_demo(payload):
    """Recognise our exact fixture bytes without trusting an upload's filename."""
    return bool(payload) and hashlib.sha256(payload).digest() == _bundled_demo_digest()


@st.cache_data(show_spinner=False, max_entries=10)
def run_cached(payload, config_values, source_name, synthetic=False):
    image = generate_demo()["image"] if synthetic and not payload else load_image(payload)
    return analyze_image(image, AnalysisConfig(**config_values), source_name=source_name, synthetic=synthetic or is_bundled_demo(payload))


def demo_result():
    return run_cached(b"", AnalysisConfig().to_dict(), "Synthetic vineyard demo", True)
