"""Interactive health map with the actual drone image as its coordinate frame."""
import plotly.graph_objects as go
from PIL import Image

from src.mapping.visualization import COLORS, LABELS, segmentation_overlay


def create_health_map(result, show_regions=True, show_segmentation=False, show_anomalies=True, show_gaps=True):
    rgb = result["image"]
    if show_segmentation:
        rgb = segmentation_overlay(rgb, result["mask"])
    height, width = rgb.shape[:2]
    fig = go.Figure()
    fig.add_layout_image(source=Image.fromarray(rgb), xref="x", yref="y", x=0, y=0, sizex=width, sizey=height, sizing="stretch", layer="below")
    for category, color in COLORS.items():
        regions = [r for r in result["regions"] if r["category"] == category]
        if show_regions or (show_anomalies and category == "RED"):
            for region in regions:
                neutral = region.get("has_canopy") is False and category != "BLACK"
                opacity = 0.04 if neutral else (0.40 if category == "RED" and show_anomalies else 0.17)
                fig.add_shape(type="rect", x0=region["x1"], y0=region["y1"], x1=region["x2"], y1=region["y2"], line={"color": "rgba(255,255,255,.45)", "width": 0.7}, fillcolor=f"rgba({color[0]},{color[1]},{color[2]},{opacity})", layer="above")
        if regions:
            data = [[r["region_id"], r["canopy_coverage"], r["anomaly_score"], "; ".join(r["issues"]) or "No visual flags", r.get("original_x1", r["x1"]), r.get("original_y1", r["y1"])] for r in regions]
            fig.add_trace(go.Scatter(x=[(r["x1"] + r["x2"]) / 2 for r in regions], y=[(r["y1"] + r["y2"]) / 2 for r in regions], mode="markers", name=LABELS[category], marker={"size": 13, "color": f"rgb{color}", "opacity": .75 if show_regions else .02, "line": {"color": "white", "width": 1}}, customdata=data, hovertemplate="<b>%{customdata[0]}</b><br>Canopy: %{customdata[1]:.1f}%<br>Anomaly score: %{customdata[2]:.2f}<br>%{customdata[3]}<br>Original pixel top-left: %{customdata[4]}, %{customdata[5]}<extra>" + LABELS[category] + "</extra>"))
    if show_gaps and result["gaps"]:
        fig.add_trace(go.Scatter(x=[(g["x1"] + g["x2"]) / 2 for g in result["gaps"]], y=[(g["y1"] + g["y2"]) / 2 for g in result["gaps"]], mode="markers", name="Possible canopy gap", marker={"color": "#111c15", "size": 17, "symbol": "x", "line": {"color": "white", "width": 1}}, hovertemplate="Possible canopy gap<br>x=%{x:.0f}, y=%{y:.0f} processed pixels<extra>Requires inspection</extra>"))
    fig.update_layout(height=max(420, min(700, int(height / width * 1000))), margin={"l": 0, "r": 0, "t": 0, "b": 25}, plot_bgcolor="#edf2ea", paper_bgcolor="rgba(0,0,0,0)", font={"color": "#18392e"}, legend={"orientation": "h", "y": -0.08, "x": 0}, dragmode="pan", uirevision=result["metadata"].get("source_name", "image"), hoverlabel={"bgcolor": "white"})
    fig.update_xaxes(range=[0, width], title="Image x (pixels)", constrain="domain", showgrid=False, zeroline=False)
    fig.update_yaxes(range=[height, 0], title="Image y (pixels)", scaleanchor="x", scaleratio=1, showgrid=False, zeroline=False)
    return fig
