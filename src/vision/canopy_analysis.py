"""Regional canopy coverage and relative growth proxies in image coordinates."""
import cv2
import numpy as np

from config import AnalysisConfig
from .canopy_segmentation import excess_green


def analyze_canopy(image: np.ndarray, mask: np.ndarray, config: AnalysisConfig) -> list[dict]:
    height, width = mask.shape
    y_edges = np.unique(np.linspace(0, height, min(config.grid_rows, height) + 1, dtype=int))
    x_edges = np.unique(np.linspace(0, width, min(config.grid_cols, width) + 1, dtype=int))
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    exg = excess_green(image)
    regions = []
    for row, (y1, y2) in enumerate(zip(y_edges[:-1], y_edges[1:])):
        for col, (x1, x2) in enumerate(zip(x_edges[:-1], x_edges[1:])):
            canopy = mask[y1:y2, x1:x2]
            n = int(np.count_nonzero(canopy))
            local_hsv = hsv[y1:y2, x1:x2]
            local_exg = exg[y1:y2, x1:x2]
            yellow = (local_hsv[..., 0] < 35) & (local_hsv[..., 1] >= 45)
            regions.append({"region_id": f"R{row + 1:02d}-C{col + 1:02d}", "row": row, "col": col,
                            "x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2),
                            "canopy_coverage": float(canopy.mean() * 100), "canopy_pixels": n,
                            "mean_greenness": float(local_exg[canopy].mean()) if n else None,
                            "yellow_fraction": float(yellow[canopy].mean()) if n else None,
                            "mean_brightness": float(local_hsv[..., 2][canopy].mean() / 255) if n else None})
    coverage = np.array([r["canopy_coverage"] for r in regions]).reshape(len(y_edges) - 1, len(x_edges) - 1)
    suitable = coverage[coverage >= config.minimum_canopy_fraction * 100]
    global_reference = float(np.median(suitable)) if suitable.size else 0.0
    for region in regions:
        r, c = region["row"], region["col"]
        neighbourhood = coverage[max(0, r - 1):r + 2, max(0, c - 1):c + 2].ravel()
        eligible = neighbourhood[neighbourhood >= config.minimum_canopy_fraction * 100]
        reference = float(np.median(eligible)) if eligible.size >= 2 else global_reference
        region["neighbour_canopy_reference"] = reference
        region["growth_ratio"] = float(region["canopy_coverage"] / reference) if reference > 0 else 1.0
        region["growth_variability"] = float(np.std(neighbourhood) / max(np.mean(neighbourhood), 1.0))
    return regions
