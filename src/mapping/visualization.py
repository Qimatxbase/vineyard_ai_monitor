"""Image-relative RGB overlays; never infer geographic positions."""
import io

import cv2
import numpy as np
from PIL import Image, ImageDraw

COLORS = {"GREEN": (49, 151, 101), "YELLOW": (234, 182, 52), "RED": (215, 76, 69), "BLACK": (20, 29, 25)}
LABELS = {"GREEN": "Normal / Healthy-looking", "YELLOW": "Low Growth / Monitor", "RED": "Potential Stress / Inspect", "BLACK": "Possible Canopy Gap"}


def png_bytes(array):
    buffer = io.BytesIO()
    if array.dtype == bool:
        array = array.astype(np.uint8) * 255
    Image.fromarray(np.asarray(array, dtype=np.uint8)).save(buffer, format="PNG")
    return buffer.getvalue()


def segmentation_overlay(image, mask, alpha=0.45):
    output = image.astype(np.float32).copy()
    output[mask.astype(bool)] = (1 - alpha) * output[mask.astype(bool)] + alpha * np.array([40, 210, 119])
    return output.clip(0, 255).astype(np.uint8)


def annotated_image(result, mode="health", opacity=0.30, show_gaps=True, show_labels=True):
    output = result["image"].copy()
    if mode == "segmentation":
        output = segmentation_overlay(output, result["mask"])
    elif mode in {"health", "anomaly"}:
        layer = output.copy()
        for region in result["regions"]:
            if mode == "anomaly" and region["category"] != "RED":
                continue
            if region.get("has_canopy") is False and region["category"] != "BLACK":
                continue
            bounds = (region["x1"], region["y1"]), (region["x2"] - 1, region["y2"] - 1)
            cv2.rectangle(layer, *bounds, COLORS[region["category"]], -1)
        output = cv2.addWeighted(layer, opacity, output, 1 - opacity, 0)
    canvas = Image.fromarray(output)
    draw = ImageDraw.Draw(canvas)
    if mode == "health":
        for region in result["regions"]:
            box = (region["x1"], region["y1"], region["x2"] - 1, region["y2"] - 1)
            draw.rectangle(box, outline=(*COLORS[region["category"]],), width=1)
            if show_labels and box[2] - box[0] > 40:
                draw.text((box[0] + 4, box[1] + 3), region["region_id"], fill="white", stroke_width=1, stroke_fill="#173c2a")
    if show_gaps:
        for gap in result["gaps"]:
            box = (gap["x1"], gap["y1"], gap["x2"] - 1, gap["y2"] - 1)
            draw.rectangle(box, outline="white", width=5)
            draw.rectangle(box, outline="#111c15", width=3)
            draw.line((box[0], box[1], box[2], box[3]), fill="#111c15", width=2)
            draw.line((box[0], box[3], box[2], box[1]), fill="#111c15", width=2)
    label = "SYNTHETIC DEMO | Requires inspection" if result["metadata"].get("synthetic") else "RGB visual screening | Requires inspection"
    if canvas.width >= 260 and canvas.height >= 28:
        draw.rectangle((0, 0, min(canvas.width, 300), 22), fill="#173c2a")
        draw.text((6, 5), label, fill="white")
    return np.array(canvas)


def health_map_png(result):
    image = Image.fromarray(annotated_image(result))
    width = max(image.width, 660)
    canvas = Image.new("RGB", (width, image.height + 98), "#f7f9f5")
    canvas.paste(image, (0, 0))
    draw = ImageDraw.Draw(canvas)
    provenance = "SYNTHETIC DEMONSTRATION" if result["metadata"].get("synthetic") else "RGB HEURISTIC ANALYSIS"
    draw.text((12, image.height + 9), f"Vineyard AI Monitor | {provenance}", fill="#18392e")
    draw.text((12, image.height + 28), "Image pixels only. Flags require field inspection. Scores are not probabilities.", fill="#18392e")
    for index, key in enumerate(COLORS):
        x = 12 + index * (width // 4)
        draw.rectangle((x, image.height + 51, x + 12, image.height + 63), fill=COLORS[key])
        draw.text((x + 17, image.height + 51), {"GREEN": "Normal-looking", "YELLOW": "Monitor", "RED": "Inspect", "BLACK": "Possible gap"}[key], fill="#18392e")
    draw.text((12, image.height + 76), f"Source: {result['metadata'].get('source_name', 'image')} | PNG grid uses processed image coordinates", fill="#18392e")
    return np.array(canvas)
