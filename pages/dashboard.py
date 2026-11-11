"""Operational dashboard composed from focused inspection views."""
from collections import Counter

import plotly.graph_objects as go
import streamlit as st

from src.mapping.health_map import create_health_map
from src.services.analysis import demo_result
from src.ui.results import metric_cards
from src.ui.session import navigate_to, open_demo


CATEGORY_NAMES = {"BLACK": "Possible gap", "RED": "Inspect", "YELLOW": "Monitor", "GREEN": "Unflagged"}
CATEGORY_COLORS = {"BLACK": "#263e32", "RED": "#d76a60", "YELLOW": "#d4a943", "GREEN": "#319765"}


def _render_heading():
    heading, actions = st.columns([2, 1], vertical_alignment="center")
    with heading:
        st.title("Dashboard")
        st.caption("Canopy coverage, inspection priorities and your next field check.")
    with actions:
        analyse, drone = st.columns(2)
        analyse.button("Analyse images", on_click=navigate_to, args=("Vineyard Analysis",), width="stretch")
        drone.button("Drone Connect", on_click=navigate_to, args=("Drone Connect",), width="stretch")


def _selected_result():
    results = st.session_state.get("results", [])
    if not results:
        with st.spinner("Preparing the demonstration dashboard…"):
            return demo_result(), None
    default_index = min(st.session_state.get("active_image_index", 0), len(results) - 1)
    if len(results) == 1:
        return results[0], 0
    if st.session_state.get("dashboard_source", default_index) not in range(len(results)):
        st.session_state.pop("dashboard_source", None)
    index = st.selectbox(
        "Inspection image", range(len(results)), index=default_index,
        format_func=lambda item: results[item]["metadata"].get("source_name", f"Image {item + 1}"),
        key="dashboard_source",
    )
    return results[index], index


def _render_health_map(result, result_index):
    with st.container(border=True):
        heading, action = st.columns([2, 1], vertical_alignment="center")
        heading.subheader("Vineyard health map")
        if result_index is None:
            action.button("Run synthetic analysis", on_click=open_demo, type="primary", width="stretch")
        else:
            action.button("Open health map", on_click=navigate_to, args=("Vineyard Health Map", result_index), width="stretch")
        figure = create_health_map(result)
        figure.update_layout(height=440, legend={"font": {"size": 10}, "y": -0.15})
        st.plotly_chart(figure, width="stretch", config={"scrollZoom": True, "displaylogo": False}, key="dashboard_health_map")
        st.caption("Hover to inspect a region. Coordinates refer to image pixels.")


def _region_distribution(regions):
    counts = Counter(region["category"] for region in regions)
    categories = list(CATEGORY_NAMES)
    figure = go.Figure(go.Bar(
        x=[counts[category] for category in categories],
        y=[CATEGORY_NAMES[category] for category in categories],
        orientation="h", marker_color=[CATEGORY_COLORS[category] for category in categories],
        text=[counts[category] for category in categories], textposition="outside",
        hovertemplate="%{y}: %{x} regions<extra></extra>",
    ))
    figure.update_layout(
        height=185, margin={"l": 0, "r": 25, "t": 0, "b": 5},
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#18392e"}, showlegend=False,
        xaxis={"visible": False, "range": [0, max(counts.values(), default=1) * 1.2 + 1]},
        yaxis={"autorange": "reversed", "showgrid": False},
    )
    return figure


def _render_priorities(result):
    with st.container(border=True):
        st.subheader("Inspection priorities")
        order = {"BLACK": 0, "RED": 1, "YELLOW": 2}
        flagged = sorted(
            (region for region in result["regions"] if region["category"] in order),
            key=lambda region: (order[region["category"]], -region["anomaly_score"]),
        )
        st.caption(f"{len(flagged)} flagged regions · Top {min(3, len(flagged))} shown")
        if not flagged:
            st.success("No regions flagged with the current settings.")
        for region in flagged[:3]:
            st.markdown(f"**{region['region_id']} · {CATEGORY_NAMES[region['category']]}**")
            st.caption("; ".join(region["issues"]) or "Review the image and verify in the field.")
        st.markdown("**Regional overview**")
        st.plotly_chart(_region_distribution(result["regions"]), width="stretch", config={"displayModeBar": False}, key="dashboard_region_distribution")


def _render_drone_status():
    drone = st.session_state.get("drone_demo", {})
    names = {"disconnected": "Disconnected", "ready": "Ready", "inspecting": "Inspection in progress", "completed": "Inspection complete"}
    status = names.get(drone.get("status"), "Disconnected")
    st.caption(f"DRONE SIMULATOR · {status} · {drone.get('captured_frames', 0)} demo frames captured. Connect from the header to try a simulated inspection.")


def render():
    _render_heading()
    result, result_index = _selected_result()
    metadata = result["metadata"]
    if metadata.get("synthetic"):
        st.caption("SYNTHETIC DEMO · Computed from a generated vineyard image; these are demonstration results.")
    else:
        st.caption("RGB IMAGE ANALYSIS · Visual screening results; flags require field inspection.")
    st.caption(f"Source: {metadata.get('source_name', 'Image')} · {result['summary']['region_count']} inspection regions · {metadata['original_width']} × {metadata['original_height']} pixels")
    metric_cards(result)
    map_column, priorities_column = st.columns([2, 1], gap="large")
    with map_column:
        _render_health_map(result, result_index)
    with priorities_column:
        _render_priorities(result)
    _render_drone_status()
    st.caption("RGB colour and coverage guide inspection; they cannot confirm disease or water stress.")
