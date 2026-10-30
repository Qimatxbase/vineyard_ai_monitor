import streamlit as st


def render():
    st.title("About Vineyard AI Monitor")
    st.write("A CPU-only hackathon MVP that turns overhead RGB drone imagery into a prioritised vineyard inspection map.")
    st.subheader("The problem")
    st.write("Vineyard managers have limited time to inspect every row. Aerial images cover large areas, but translating them into specific inspection locations takes effort. This tool highlights visible canopy differences and candidate gaps so a manager can decide where to look first.")
    st.subheader("How it works")
    st.markdown("""
1. **Read and prepare RGB images.** Decode JPG, PNG or TIFF, honour EXIF orientation, and retain a mapping back to original pixels.
2. **Segment visible vegetation.** Combine excess-green and HSV colour evidence, then remove small components and filter the mask.
3. **Look for row-supported gaps.** Estimate repeated parallel row bands and flag wide interior gaps between populated canopy segments. Withhold gap findings when structure is insufficient.
4. **Compare regions.** Measure canopy coverage, local growth variation and relative colour differences. These feed explicit inspection rules.
5. **Map and export.** Show the actual image with region classifications, inspection statistics and candidate gap markers; export CSV, JSON and PNG results.
""")
    st.subheader("What the colours mean")
    st.markdown("""
- 🟢 **Normal / Healthy-looking:** visible canopy without a current inspection flag.
- 🟡 **Low Growth / Monitor:** low relative canopy coverage; empty regions carry an explicit uncertainty label.
- 🔴 **Potential Stress / Inspect:** unusual relative canopy colour and/or density. A visual anomaly score, not a probability.
- ⚫ **Possible Canopy Gap:** a candidate interior gap along a supported row, never a confirmed missing vine.
""")
    with st.expander("Transparent scoring rules"):
        st.write("Visual anomaly score = 0.55 × relative greenness deficit + 0.30 × scaled yellow-canopy fraction + 0.15 × relative coverage deficit. Greenness uses a median/MAD reference across canopy-bearing regions. Scores are clipped to [0,1] and are not calibrated probabilities.")
        st.write("Classification order: candidate-gap centre → BLACK; anomaly score at or above the chosen threshold → RED; canopy coverage below the chosen fraction of a suitable local reference → YELLOW; otherwise GREEN. Regions with insufficient visible canopy are marked YELLOW and uncertain. Defaults: anomaly threshold 0.55 and low-growth ratio 0.55.")
    st.subheader("Dataset")
    st.markdown("[Zenodo: Aerial RGB and Thermal Infrared Images of Vineyards](https://zenodo.org/records/13862443) contains 375 images in each of three collections: RGB, thermal, and pseudo-colour references. Archive directories and filenames are documented in `docs/DATASET.md`. Download and extract RGB images manually; the app does not download the archives.")
    st.write("This MVP analyses RGB only. The pseudo-colour references are cropped/aligned to thermal field of view according to the dataset description; they are not automatically accepted as independent segmentation labels or assumed to align with full-resolution RGB images.")
    st.subheader("Current limits and next steps")
    st.write("Colour thresholds respond to lighting, shadows, soil, weeds and season. The vegetation mask can include non-vine plants and miss brown or yellow canopy. Row detection assumes repeated, approximately straight rows; curved or irregular planting and orthomosaic artefacts can break it. Fixed image tiles can split plants and reflect row spacing as well as growth.")
    st.write("No GPS positions, plant counts, biomass, disease diagnosis or water-stress diagnosis are inferred. Field accuracy requires independently annotated real images. Future work could add a validated vine-specific segmentation model, reviewed RGB/thermal registration, and genuine georeferenced mapping.")
    st.subheader("Four-person team")
    st.table({"Role": ["Business & Product", "Core AI", "Evaluation", "Data & Dashboard"], "Ownership": ["Farmer use case, value proposition and pitch", "Segmentation, rows, gaps, regional analysis and pipeline", "Ground truth, metrics, error analysis and tests", "Image loading, dashboard, health map and exports"]})
