"""Portable exports with analysis settings, provenance and original-pixel mapping."""
import io
import json
import re
import zipfile

import numpy as np
import pandas as pd
from PIL import Image

from src.mapping.visualization import annotated_image, health_map_png, png_bytes


def _serializable(value):
    if isinstance(value, dict):
        return {str(k): _serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serializable(v) for v in value]
    if isinstance(value, np.ndarray):
        return _serializable(value.tolist())
    if isinstance(value, np.generic):
        return _serializable(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def result_json(result):
    document = {k: v for k, v in result.items() if k not in {"image", "mask"}}
    document["interpretation"] = "RGB heuristic visual screening, not disease diagnosis, water-stress proof, calibrated probability, biomass measurement or GPS mapping. Field inspection required."
    document["coordinates"] = "x1/y1 inclusive; x2/y2 exclusive. Region and gap coordinates use processed pixels; original_* fields use original pixels. Canopy mask PNG is rescaled to original dimensions with nearest-neighbour interpolation."
    return json.dumps(_serializable(document), indent=2, allow_nan=False).encode("utf-8")


def regions_csv(result):
    frame = pd.DataFrame(result["regions"])
    if "issues" in frame:
        frame["issues"] = frame["issues"].map(lambda values: "; ".join(values))
    frame.insert(0, "source_name", result["metadata"].get("source_name", "image"))
    frame.insert(1, "synthetic", result["metadata"].get("synthetic", False))
    return frame.to_csv(index=False).encode("utf-8")


def original_mask_png(result):
    mask = Image.fromarray(result["mask"].astype(np.uint8) * 255)
    metadata = result["metadata"]
    size = (metadata["original_width"], metadata["original_height"])
    if mask.size != size:
        mask = mask.resize(size, Image.Resampling.NEAREST)
    output = io.BytesIO()
    mask.save(output, format="PNG")
    return output.getvalue()


def export_bundle(result):
    files = {
        "analysis.json": result_json(result),
        "regions.csv": regions_csv(result),
        "canopy_mask.png": original_mask_png(result),
        "annotated.png": png_bytes(annotated_image(result)),
        "health_map.png": png_bytes(health_map_png(result)),
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()


def batch_bundle(results):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        summaries = []
        for index, result in enumerate(results):
            source = result["metadata"].get("source_name", "image")
            stem = re.sub(r"[^a-zA-Z0-9_-]", "_", source)[:70] or "image"
            archive.writestr(f"{index + 1:02d}_{stem}.zip", export_bundle(result))
            summaries.append({"source_name": source, "synthetic": result["metadata"].get("synthetic", False), **result["summary"]})
        archive.writestr("batch_summary.csv", pd.DataFrame(summaries).to_csv(index=False))
    return output.getvalue()
