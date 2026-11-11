"""Local entry point: python -m streamlit run app.py."""
import logging

import streamlit as st


def main() -> None:
    st.set_page_config(
        page_title="Vineyard AI Monitor", page_icon="🌿", layout="wide",
        initial_sidebar_state="collapsed",
    )
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from src.ui.application import render_app
    render_app()


if __name__ == "__main__":
    main()
