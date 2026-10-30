import io
import hashlib
import json

import numpy as np
from PIL import Image
import streamlit as st

from src.dashboard import active_result, provenance
from src.data.synthetic import generate_demo
from src.evaluation.evaluate import evaluate_segmentation, load_boxes_json, load_ground_truth_mask
from src.evaluation.metrics import detection_metrics
from src.mapping.visualization import png_bytes
from src.utils.export import original_mask_png


def _evaluation_key(result, task, annotation, extra=""):
    if isinstance(annotation, np.ndarray):
        annotation = annotation.tobytes()
    elif hasattr(annotation, "getvalue"):
        annotation = annotation.getvalue()
    elif not isinstance(annotation, bytes):
        annotation = json.dumps(annotation).encode()
    digest = hashlib.sha256(annotation).hexdigest()
    return (result["metadata"]["source_name"], result["summary"]["processing_seconds"], digest, extra)


def _mask_original(result, anomaly=False):
    if not anomaly:
        return np.array(Image.open(io.BytesIO(original_mask_png(result)))) > 0
    mask = np.zeros(result["mask"].shape, dtype=bool)
    for region in result["regions"]:
        if region["category"] == "RED":
            mask[region["y1"]:region["y2"], region["x1"]:region["x2"]] = True
    mask &= result["mask"]
    metadata = result["metadata"]
    image = Image.fromarray(mask.astype(np.uint8) * 255).resize((metadata["original_width"], metadata["original_height"]), Image.Resampling.NEAREST)
    return np.array(image) > 0


def _report(result, metrics, task, synthetic_annotations):
    report = {"task": task, "source_name": result["metadata"]["source_name"], "synthetic_image": result["metadata"]["synthetic"], "synthetic_annotations": synthetic_annotations, "annotation_provenance": "Generated demonstration shapes; software check only" if synthetic_annotations else "User-supplied annotations; semantic independence and crop alignment require verification", "processing_seconds": result["summary"]["processing_seconds"], "metrics": metrics, "config": result["config"], "coordinate_frame": "EXIF-oriented original image pixels", "empty_set_convention": "Both sets empty: scores 1. No ground-truth positives: recall 1; false positives reduce precision and F1."}
    st.download_button("Download evaluation JSON", json.dumps(report, indent=2).encode(), f"{task}_evaluation.json", "application/json", key=f"download_eval_{task}")


def _show_mask_evaluation(result, truth, task, synthetic_annotations):
    prediction = _mask_original(result, anomaly=task == "visual_anomaly")
    expected = prediction.shape
    truth = load_ground_truth_mask(truth, expected_shape=expected)
    evaluation = evaluate_segmentation(prediction, truth)
    scores = evaluation["metrics"]
    columns = st.columns(5)
    for column, (label, key) in zip(columns, [("IoU", "intersection_over_union"), ("Dice", "dice"), ("Precision", "precision"), ("Recall", "recall"), ("F1", "f1")]):
        column.metric(label, f"{scores[key]:.3f}")
    st.caption(f"TP {scores['tp']:,} · FP {scores['fp']:,} · FN {scores['fn']:,} · TN {scores['tn']:,} pixels")
    a, b, c = st.columns(3)
    a.image(prediction.astype(np.uint8) * 255, caption="Prediction", width="stretch")
    b.image(truth.astype(np.uint8) * 255, caption="Supplied annotation", width="stretch")
    c.image(evaluation["confusion"], caption="Green TP · Red FP · Blue FN · Grey TN", width="stretch")
    _report(result, scores, task, synthetic_annotations)
    st.download_button("Download error overlay PNG", png_bytes(evaluation["confusion"]), f"{task}_errors.png", "image/png", key=f"errors_{task}")


def render():
    st.title("Evaluation")
    st.write("Compare predictions against annotations for the same image, crop and coordinate frame. Scores appear only when annotations are supplied.")
    result = active_result()
    if result is None:
        return
    provenance(result)
    st.caption(f"Pipeline processing time: {result['summary']['processing_seconds']:.3f} seconds. Cached views reuse the recorded run time; this is not a hardware benchmark.")
    use_synthetic = st.toggle("Use synthetic demonstration annotations", value=False, disabled=not result["metadata"].get("synthetic", False)) and result["metadata"].get("synthetic", False)
    if use_synthetic:
        st.warning("Software demonstration only: these annotations describe the generated shapes and do not establish real vineyard accuracy.")
    st.info("Masks must be binary grayscale PNG/TIFF (0 and 1 or 255) at the original, EXIF-oriented image dimensions. No ground-truth resizing or automatic pseudo-colour conversion is performed.")
    tabs = st.tabs(["Canopy segmentation", "Possible gap detection", "Visual anomaly regions"])
    with tabs[0]:
        upload = st.file_uploader("Independent canopy mask", type=["png", "tif", "tiff"], key="canopy_gt")
        truth = generate_demo()["canopy_mask"] if use_synthetic else upload
        if truth is None:
            st.caption("No canopy ground truth supplied. IoU and Dice are unavailable.")
        else:
            key = _evaluation_key(result, "canopy", truth)
            if st.button("Evaluate canopy segmentation", type="primary"):
                st.session_state["canopy_evaluation_key"] = key
            if st.session_state.get("canopy_evaluation_key") == key:
                try:
                    _show_mask_evaluation(result, truth, "canopy", use_synthetic)
                except (ValueError, OSError) as exc:
                    st.error(str(exc))
    with tabs[1]:
        st.caption('Upload JSON: {"boxes": [[x1, y1, x2, y2], ...]}. Boxes use original image pixels; x2/y2 are exclusive. An empty list is an explicit annotation of no gaps.')
        upload = st.file_uploader("Independently annotated canopy-gap boxes", type=["json"], key="gaps_gt")
        threshold = st.slider("Box matching IoU threshold", 0.10, 1.0, 0.50, 0.05)
        if not use_synthetic and upload is None:
            st.caption("No gap ground truth supplied. Detection metrics are unavailable.")
        else:
            key = _evaluation_key(result, "gaps", generate_demo()["gap_boxes"] if use_synthetic else upload, threshold)
            if st.button("Evaluate possible gaps", type="primary"):
                st.session_state["gaps_evaluation_key"] = key
            if st.session_state.get("gaps_evaluation_key") == key:
                try:
                    truth = generate_demo()["gap_boxes"] if use_synthetic else load_boxes_json(upload)
                    metadata = result["metadata"]
                    if any(box[2] > metadata["original_width"] or box[3] > metadata["original_height"] for box in truth):
                        raise ValueError("An annotation box extends beyond the original image dimensions.")
                    predictions = [[gap["original_" + field] for field in ("x1", "y1", "x2", "y2")] for gap in result["gaps"]]
                    scores = detection_metrics(predictions, truth, threshold)
                    for column, field in zip(st.columns(3), ["precision", "recall", "f1"]):
                        column.metric(field.title(), f"{scores[field]:.3f}")
                    st.caption(f"TP {scores['tp']} · FP {scores['fp']} · FN {scores['fn']} · One-to-one box matching")
                    _report(result, scores, "canopy_gaps", use_synthetic)
                    st.dataframe(scores["matches"], width="stretch")
                except (ValueError, OSError) as exc:
                    st.error(str(exc))
    with tabs[2]:
        st.caption("Prediction: RED-classified region cells intersected with detected canopy. Metrics compare visible flagged area with a binary anomaly annotation. These are pixel metrics, not disease-diagnosis accuracy.")
        upload = st.file_uploader("Independent visual anomaly mask", type=["png", "tif", "tiff"], key="anomaly_gt")
        truth = generate_demo()["anomaly_mask"] if use_synthetic else upload
        if truth is None:
            st.caption("No suitable anomaly ground truth supplied. Precision, recall and F1 are unavailable.")
        else:
            key = _evaluation_key(result, "anomaly", truth)
            if st.button("Evaluate visual anomalies", type="primary"):
                st.session_state["anomaly_evaluation_key"] = key
            if st.session_state.get("anomaly_evaluation_key") == key:
                try:
                    _show_mask_evaluation(result, truth, "visual_anomaly", use_synthetic)
                except (ValueError, OSError) as exc:
                    st.error(str(exc))
    st.caption("Metric convention: both foreground sets empty → 1.0. No ground-truth positives → recall 1.0; false positives still lower precision and F1. See docs/EVALUATION.md for details.")
