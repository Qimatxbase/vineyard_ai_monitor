"""Load local stylesheets shared by the Streamlit pages."""
from pathlib import Path

import streamlit as st


STYLE_DIRECTORY = Path(__file__).resolve().parents[2] / "assets" / "styles"


def inject_styles(filename: str) -> None:
    css = (STYLE_DIRECTORY / filename).read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
