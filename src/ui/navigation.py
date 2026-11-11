"""The shared top bar; page order comes from the application route registry."""
from collections.abc import Sequence

import streamlit as st

from src.ui.session import on_navigation_change


PAGE_LABELS = {
    "Vineyard Analysis": "Analysis",
    "Vineyard Health Map": "Health map",
    "Drone Connect": "Drone connect",
}


def render_header(pages: Sequence[str]) -> str:
    if st.session_state.get("workspace_page") not in pages or st.session_state.get("workspace_page") == "Overview":
        st.session_state["workspace_page"] = "Dashboard"

    with st.container(key="workspace_header"):
        brand, navigation, connection = st.columns([1.3, 5.65, 1.1], vertical_alignment="center", gap="small")
        with brand:
            st.markdown('<div class="brand">Vineyard<small>FIELD MONITOR</small></div>', unsafe_allow_html=True)
        with navigation:
            page = st.radio(
                "Main navigation", pages,
                format_func=lambda value: PAGE_LABELS.get(value, value),
                horizontal=True, key="workspace_page", on_change=on_navigation_change,
                label_visibility="collapsed",
            )
        with connection:
            connected = st.session_state.get("drone_demo", {}).get("status", "disconnected") != "disconnected"
            label = "Demo drone connected" if connected else "Demo drone offline"
            css_class = "connection-pill connected" if connected else "connection-pill"
            st.markdown(f'<div class="{css_class}"><span></span>{label}</div>', unsafe_allow_html=True)
    return page
