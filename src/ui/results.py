"""Shared result views, inspection tables and download controls."""
import pandas as pd
import streamlit as st

from src.mapping.visualization import LABELS, annotated_image, health_map_png, png_bytes
from src.ui.session import open_demo
from src.utils.export import batch_bundle, export_bundle, original_mask_png, regions_csv, result_json


def active_result():
    results = st.session_state.get("results", [])
    if not results:
        st.info("Run an analysis or open the synthetic demo to view inspection results.")
        st.button("Open synthetic demo", on_click=open_demo, type="primary")
        return None
    index = st.selectbox("Active image", options=list(range(len(results))), format_func=lambda i: results[i]["metadata"].get("source_name", f"Image {i + 1}"), key="active_image_index")
    return results[index]


def provenance(result):
    metadata = result["metadata"]
    if metadata.get("synthetic"):
        st.warning("SYNTHETIC DEMO · Generated vineyard illustration. These analysis results are not measurements from a real vineyard.")
    else:
        st.caption("RGB visual screening · Findings require field inspection. Anomaly scores are heuristic scores, not probabilities.")
    st.caption(f"Original: {metadata['original_width']} × {metadata['original_height']} px · Analysed: {metadata['processed_width']} × {metadata['processed_height']} px · {result['summary']['processing_seconds']:.2f} s · Image-relative coordinates")


def metric_cards(result):
    summary = result["summary"]
    with st.container(key="summary_metrics"):
        columns = st.columns(4)
        columns[0].metric("Visible canopy", f"{summary['canopy_coverage']:.1f}%")
        columns[1].metric("Potential stress regions", str(summary["anomaly_count"]))
        columns[2].metric("Possible canopy gaps", str(summary["gap_count"]))
        columns[3].metric("Low-growth regions", str(summary["low_growth_count"]))


def show_warnings(result):
    for message in dict.fromkeys(result.get("warnings", [])):
        st.info(message)
    info = result.get("row_info", {})
    if info.get("available"):
        st.caption(f"Row orientation estimate: {info.get('angle_degrees', 0):.1f}° · Structure score: {info.get('confidence', 0):.2f} · Gap findings remain candidates.")
    elif info.get("message"):
        st.info(info["message"])


def result_images(result):
    tabs = st.tabs(["Canopy segmentation", "Visual anomalies", "Possible gaps", "Original image"])
    with tabs[0]:
        columns = st.columns([2, 1])
        columns[0].image(annotated_image(result, "segmentation", show_gaps=False), caption="Green overlay: detected visible vegetation", width="stretch")
        columns[1].image(result["mask"].astype("uint8") * 255, caption="Binary canopy mask", width="stretch")
    with tabs[1]:
        st.image(annotated_image(result, "anomaly", show_gaps=False), caption="Potential stress / visual anomaly regions. Colour alone cannot diagnose disease or water stress.", width="stretch")
    with tabs[2]:
        st.image(annotated_image(result, "original", show_gaps=True), caption="Black boxes: possible canopy gaps supported by visible row structure.", width="stretch")
    with tabs[3]:
        st.image(result["image"], caption="RGB image at analysis resolution", width="stretch")


def downloads(result):
    with st.expander("Download analysis results", expanded=False):
        st.caption("CSV and JSON include original pixel coordinates. The mask PNG uses original dimensions; annotated images and maps use analysis dimensions.")
        columns = st.columns(3)
        columns[0].download_button("Complete result ZIP", export_bundle(result), "vineyard_analysis.zip", "application/zip", width="stretch")
        columns[1].download_button("Regional CSV", regions_csv(result), "vineyard_regions.csv", "text/csv", width="stretch")
        columns[2].download_button("Structured JSON", result_json(result), "vineyard_analysis.json", "application/json", width="stretch")
        columns[0].download_button("Canopy mask PNG", original_mask_png(result), "canopy_mask.png", "image/png", width="stretch")
        columns[1].download_button("Annotated image PNG", png_bytes(annotated_image(result)), "annotated.png", "image/png", width="stretch")
        columns[2].download_button("Health map PNG", png_bytes(health_map_png(result)), "health_map.png", "image/png", width="stretch")
        results = st.session_state.get("results", [])
        if len(results) > 1:
            st.download_button("Download all images + batch summary", batch_bundle(results), "vineyard_batch.zip", "application/zip")


def region_table(result, only_flagged=False):
    frame = pd.DataFrame(result["regions"])
    if frame.empty:
        return frame
    frame["inspection_category"] = frame["category"].map(LABELS)
    frame["issues"] = frame["issues"].map(lambda items: "; ".join(items))
    order = {"BLACK": 0, "RED": 1, "YELLOW": 2, "GREEN": 3}
    frame["_priority"] = frame["category"].map(order)
    frame = frame.sort_values(["_priority", "anomaly_score"], ascending=[True, False])
    if only_flagged:
        frame = frame[frame["category"] != "GREEN"]
    columns = ["region_id", "inspection_category", "canopy_coverage", "growth_variability", "anomaly_score", "original_x1", "original_y1", "original_x2", "original_y2", "issues"]
    return frame[[c for c in columns if c in frame]]
