import streamlit as st

from src.dashboard import demo_result, metric_cards, open_demo
from src.mapping.health_map import create_health_map


def render():
    st.markdown('<div class="hero"><div class="eyebrow">FIELD INTELLIGENCE · HACKATHON MVP</div><h1>Every row tells a story.</h1><p>Turn RGB drone imagery into a clear vineyard inspection map. Find canopy gaps, compare growth, and focus attention on unusual regions.</p></div>', unsafe_allow_html=True)
    st.button("Try the synthetic vineyard demo →", type="primary", on_click=open_demo)
    st.caption("Have your own drone images? Open Vineyard Analysis to upload JPG, PNG or TIFF images, or choose a local folder.")
    st.subheader("From overhead view to on-the-ground priorities")
    steps = [("01 / UPLOAD", "Bring your drone image", "Single images or a batch. RGB is all you need for the baseline."), ("02 / ANALYSE", "Read the visible canopy", "Segment vegetation, compare regional coverage and flag unusual colours."), ("03 / INSPECT", "Know where to look", "Explore the health map, review candidate gaps and export inspection results.")]
    for column, (eyebrow, title, text) in zip(st.columns(3), steps):
        column.markdown(f'<div class="step"><small>{eyebrow}</small><h3>{title}</h3><p>{text}</p></div>', unsafe_allow_html=True)
    st.subheader("A vineyard inspection map, in one view")
    st.caption("SYNTHETIC DEMONSTRATION · The map and metrics below are computed from a generated illustration, not a real vineyard.")
    with st.spinner("Preparing the synthetic vineyard demonstration…"):
        result = demo_result()
    metric_cards(result)
    st.plotly_chart(create_health_map(result), width="stretch", config={"scrollZoom": True, "displaylogo": False})
    st.caption("Green: healthy-looking canopy · Yellow: low growth / monitor · Red: potential stress / inspect · Black: possible canopy gap. Pan, zoom and hover over region markers.")
    st.info("A screening tool for farmer inspection. RGB colour and coverage cannot confirm disease, water stress, total biomass or missing plants.")
