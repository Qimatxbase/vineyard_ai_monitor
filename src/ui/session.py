"""Shared workspace navigation and analysis-result session actions."""
import streamlit as st


def navigate_to(page: str, result_index: int | None = None) -> None:
    st.session_state["workspace_page"] = page
    st.session_state["workspace_entered"] = page != "Overview"
    if result_index is not None:
        st.session_state["active_image_index"] = result_index


def enter_workspace() -> None:
    navigate_to("Dashboard")


def open_demo() -> None:
    st.session_state["demo_requested"] = True
    navigate_to("Vineyard Analysis")


def store_results(results: list[dict]) -> None:
    st.session_state["results"] = results
    st.session_state.pop("active_image_index", None)


def on_navigation_change() -> None:
    navigate_to(st.session_state["workspace_page"])
