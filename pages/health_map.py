import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard import active_result, downloads, metric_cards, provenance, region_table, show_warnings
from src.mapping.health_map import create_health_map
from src.mapping.visualization import LABELS


def render():
    st.title("Vineyard Health Map")
    st.write("Explore the image, compare canopy regions, and choose where to inspect first.")
    result = active_result()
    if result is None:
        return
    provenance(result)
    metric_cards(result)
    a, b, c, d = st.columns(4)
    regions = a.toggle("Region colours", True)
    canopy = b.toggle("Canopy overlay", False)
    anomaly = c.toggle("Emphasise anomalies", True)
    gaps = d.toggle("Possible gap markers", True)
    st.plotly_chart(create_health_map(result, regions, canopy, anomaly, gaps), width="stretch", config={"scrollZoom": True, "displaylogo": False})
    st.caption("Pan and zoom with the chart controls. Hover over region centres for statistics. Axes are image pixels, not GPS positions.")
    show_warnings(result)
    st.subheader("Inspect a region")
    regions_by_id = {item["region_id"]: item for item in result["regions"]}
    region_id = st.selectbox("Region", list(regions_by_id))
    region = regions_by_id[region_id]
    left, right = st.columns([1, 2])
    left.image(result["image"][region["y1"]:region["y2"], region["x1"]:region["x2"]], caption=f"{region_id} · selected RGB region", width="stretch")
    with right:
        st.markdown(f"**{LABELS[region['category']]}**")
        st.write(f"Visible canopy: **{region['canopy_coverage']:.1f}%** · Anomaly score: **{region['anomaly_score']:.2f}**")
        st.write("; ".join(region["issues"]) or "No visual inspection flags under the current settings.")
        st.caption(f"Original image pixels: ({region.get('original_x1', region['x1'])}, {region.get('original_y1', region['y1'])}) → ({region.get('original_x2', region['x2'])}, {region.get('original_y2', region['y2'])}). Coordinates refer to the EXIF-oriented image.")
    st.subheader("Inspection queue")
    only = st.checkbox("Show only flagged regions", True)
    table = region_table(result, only)
    if table.empty:
        st.success("No regions exceeded the current inspection thresholds.")
    else:
        st.dataframe(table, hide_index=True, width="stretch", column_config={"canopy_coverage": st.column_config.NumberColumn("Canopy %", format="%.1f"), "anomaly_score": st.column_config.NumberColumn("Anomaly score", format="%.2f"), "growth_variability": st.column_config.NumberColumn("Growth variability", format="%.2f")})
    if result["gaps"]:
        with st.expander("Possible gap locations"):
            st.dataframe(pd.DataFrame(result["gaps"]), hide_index=True, width="stretch")
    st.subheader("Compare regional patterns")
    frame = pd.DataFrame(result["regions"])
    left, right = st.columns(2)
    density = frame.pivot(index="row", columns="col", values="canopy_coverage")
    fig = px.imshow(density, color_continuous_scale="YlGn", zmin=0, zmax=100, labels={"color": "Canopy %", "x": "Grid column", "y": "Grid row"}, title="Visible canopy coverage")
    fig.update_layout(margin={"l": 10, "r": 10, "t": 50, "b": 10}, paper_bgcolor="rgba(0,0,0,0)")
    left.plotly_chart(fig, width="stretch")
    fig = px.bar(frame, x="region_id", y="anomaly_score", color="category", color_discrete_map={"GREEN": "#319765", "YELLOW": "#eab634", "RED": "#d74c45", "BLACK": "#141d19"}, title="Relative visual anomaly scores")
    fig.add_hline(y=result["config"]["anomaly_threshold"], line_dash="dot", annotation_text="Inspection threshold")
    fig.update_layout(yaxis_range=[0, 1], xaxis_title="Region", yaxis_title="Score (not probability)", showlegend=False, margin={"l": 10, "r": 10, "t": 50, "b": 10}, paper_bgcolor="rgba(0,0,0,0)")
    right.plotly_chart(fig, width="stretch")
    downloads(result)
