import logging
from pathlib import Path

import streamlit as st

from config import AnalysisConfig
from src.data.dataset_loader import list_images, load_image
from src.data.synthetic import generate_demo
from src.runtime import is_public_demo
from src.services.analysis import run_cached
from src.ui.results import active_result, downloads, metric_cards, provenance, result_images, show_warnings
from src.ui.session import store_results

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def render():
    st.title("Vineyard Analysis")
    st.write("Upload an overhead RGB image, adjust the analysis, and generate an inspection map.")
    public = is_public_demo()
    max_images = 3 if public else 12
    max_file_mb = 10 if public else 100
    max_file_bytes = max_file_mb * 1024 * 1024
    source_options = ["Upload images", "Synthetic demo"] if public else ["Upload images", "Local folder", "Synthetic demo"]
    requested = st.session_state.pop("demo_requested", False)
    if requested:
        st.session_state["source_choice"] = "Synthetic demo"
    if st.session_state.get("source_choice", "Upload images") not in source_options:
        st.session_state["source_choice"] = "Upload images"
    source = st.radio("Image source", source_options, horizontal=True, key="source_choice")
    inputs = []
    if source == "Upload images":
        uploaded = st.file_uploader("RGB drone images", type=["jpg", "jpeg", "png", "tif", "tiff"], accept_multiple_files=True, help=f"Up to {max_images} images per analysis, {max_file_mb} MB and 40 million pixels per image.")
        for item in uploaded[:max_images]:
            if item.size > max_file_bytes:
                st.error(f"{item.name}: exceeds the {max_file_mb} MB input limit.")
            else:
                inputs.append((item.name, item.getvalue()))
        if len(uploaded) > max_images:
            st.warning(f"The first {max_images} images will be analysed. Split larger collections into batches.")
    elif source == "Local folder" and not public:
        folder = st.text_input("Local RGB image folder", value=str(ROOT / "data" / "raw"))
        if st.button("Scan folder"):
            try:
                st.session_state["folder_images"] = [str(path.resolve()) for path in list_images(Path(folder).expanduser().resolve())]
                st.session_state["scanned_folder"] = folder
            except (ValueError, OSError) as exc:
                st.error(str(exc))
        if st.session_state.get("scanned_folder") == folder:
            paths = st.session_state.get("folder_images", [])
            if not paths:
                st.info("No supported images found. Add extracted RGB images to this folder, then scan again.")
            chosen = st.multiselect("Images to analyse (maximum 12)", paths, default=paths[:1], format_func=lambda path: str(Path(path).relative_to(Path(folder).expanduser().resolve())) if Path(path).is_absolute() else path)
            for path in chosen[:12]:
                try:
                    if Path(path).stat().st_size > 100 * 1024 * 1024:
                        raise ValueError(f"{Path(path).name}: exceeds the 100 MB input limit.")
                    inputs.append((str(Path(path).relative_to(Path(folder).expanduser().resolve())), Path(path).read_bytes()))
                except (ValueError, OSError) as exc:
                    st.error(str(exc))
            if len(chosen) > 12:
                st.warning("The first 12 selected images will be analysed.")
    elif source == "Synthetic demo":
        st.warning("Synthetic demonstration: generated vineyard rows with deliberately introduced gaps and yellow canopy. Suitable for demonstrating the workflow, not field validation.")
        inputs = [("Synthetic vineyard demo", b"")]
    if inputs:
        try:
            preview = generate_demo()["image"] if source == "Synthetic demo" else load_image(inputs[0][1])
            with st.expander("Preview input image", expanded=not st.session_state.get("results")):
                st.image(preview, caption=inputs[0][0], width="stretch")
                if len(inputs) > 1:
                    st.caption(f"Previewing the first of {len(inputs)} selected images.")
        except (ValueError, OSError) as exc:
            st.error(f"Cannot preview this image: {exc}")
    with st.expander("Analysis settings", expanded=False):
        left, middle, right = st.columns(3)
        with left:
            st.markdown("**Canopy detection**")
            mode = st.selectbox("Segmentation method", ["combined", "exg", "hsv", "otsu"], help="Combined uses green colour and excess-green evidence. Yellow/brown canopy may be missed.")
            exg = st.slider("Excess-green threshold", -0.10, 0.50, 0.08, 0.01)
            saturation = st.slider("Minimum colour saturation", 0, 150, 35, 5)
            area = st.number_input("Minimum vegetation component (pixels)", 0, 1000, 30, step=5)
        with middle:
            st.markdown("**Regional inspection**")
            rows = st.slider("Grid rows", 2, 20, 8)
            cols = st.slider("Grid columns", 2, 20, 10)
            anomaly = st.slider("Potential stress threshold", 0.10, 1.0, 0.55, 0.05, help="A relative visual anomaly score, not a probability. A lower threshold flags more regions.")
            growth = st.slider("Low-growth ratio", 0.10, 0.95, 0.55, 0.05, help="Coverage compared with a suitable local canopy reference.")
        with right:
            st.markdown("**Image & row structure**")
            size = st.selectbox("Maximum analysis side (pixels)", [1024, 1600, 2400, 3200], index=1)
            gap = st.slider("Gap size sensitivity", 0.50, 3.0, 1.50, 0.10, help="Larger values require wider gaps along supported vine rows.")
            tile = st.selectbox("Segmentation tile size", [0, 512, 1024], format_func=lambda value: "Whole image" if value == 0 else f"{value} pixels")
            st.caption("Original dimensions and coordinate mapping are preserved. No GPS coordinates are inferred.")
    settings = AnalysisConfig(max_dimension=size, grid_rows=rows, grid_cols=cols, exg_threshold=exg, saturation_min=saturation, min_component_area=area, gap_sensitivity=gap, anomaly_threshold=anomaly, low_growth_ratio=growth, segmentation_mode=mode, tile_size=tile)
    run = st.button("Analyse Vineyard", type="primary", disabled=not inputs, width="stretch")
    if (run or requested) and inputs:
        progress = st.progress(0, text="Preparing analysis…")
        results = []
        for index, (name, payload) in enumerate(inputs):
            progress.progress(index / len(inputs), text=f"Analysing {index + 1}/{len(inputs)}: {name}")
            try:
                results.append(run_cached(payload, settings.to_dict(), name, source == "Synthetic demo"))
            except Exception as exc:
                LOGGER.exception("Analysis failed for %s", name)
                st.error(f"{name}: {exc}")
        progress.empty()
        if results:
            store_results(results)
            st.success(f"Analysis complete for {len(results)} image(s). Open Vineyard Health Map to explore inspection priorities.")
    if st.session_state.get("results"):
        st.divider()
        st.subheader("Analysis results")
        result = active_result()
        provenance(result)
        metric_cards(result)
        show_warnings(result)
        result_images(result)
        downloads(result)
