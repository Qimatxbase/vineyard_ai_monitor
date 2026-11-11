"""Application composition and a single ordered registry for all pages."""
import streamlit as st

from pages import analysis, dashboard, drone_connect, evaluation, health_map, welcome
from src.ui.navigation import render_header
from src.ui.styles import inject_styles


PAGE_ROUTES = {
    "Overview": welcome.render,
    "Dashboard": dashboard.render,
    "Vineyard Analysis": analysis.render,
    "Vineyard Health Map": health_map.render,
    "Drone Connect": drone_connect.render,
    "Evaluation": evaluation.render,
}


def render_app() -> None:
    inject_styles("base.css")
    if not st.session_state.get("workspace_entered", False):
        welcome.render()
        return
    page = render_header(tuple(PAGE_ROUTES))
    PAGE_ROUTES[page]()
