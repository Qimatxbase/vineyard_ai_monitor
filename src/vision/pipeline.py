"""End-to-end deterministic RGB image analysis with original-coordinate mapping."""
import logging
from time import perf_counter

import numpy as np

from config import AnalysisConfig
from src.data.preprocessing import prepare_image
from .anomaly_detection import score_anomalies
from .canopy_analysis import analyze_canopy
from .canopy_segmentation import segment_canopy, validate_rgb
from .missing_vines import detect_missing_vines
from .row_detection import detect_rows

LOGGER = logging.getLogger(__name__)


def analyze_image(image: np.ndarray, config: AnalysisConfig | None = None,
                  source_name: str = "image", synthetic: bool = False) -> dict:
    started = perf_counter()
    config = config or AnalysisConfig()
    image = validate_rgb(image)
    original_height, original_width = image.shape[:2]
    image, mapping = prepare_image(image, config.max_dimension)
    height, width = image.shape[:2]
    scale_x, scale_y = mapping["scale_x"], mapping["scale_y"]
    mask = segment_canopy(image, config)
    row_info = detect_rows(mask)
    gaps = detect_missing_vines(mask, row_info, config.gap_sensitivity)
    regions = score_anomalies(analyze_canopy(image, mask, config), gaps, config)
    for record in [*regions, *gaps]:
        for field, scale in (("x1", scale_x), ("y1", scale_y), ("x2", scale_x), ("y2", scale_y)):
            record["original_" + field] = int(round(record[field] * scale))
    warnings = []
    if synthetic:
        warnings.append("Synthetic demonstration image. These results are not measurements on a real vineyard.")
    if not mask.any():
        warnings.append("No vegetation detected. Check RGB image content and segmentation thresholds.")
    if not row_info["available"]:
        warnings.append(row_info["message"])
    if sum(r["colour_reference_available"] for r in regions) == 0:
        warnings.append("Too few canopy-bearing regions for a robust relative colour reference.")
    warnings.append("RGB appearance and canopy coverage are inspection cues, not disease, water-stress or biomass measurements.")
    summary = {"canopy_coverage": float(mask.mean() * 100), "gap_count": len(gaps),
               "anomaly_count": sum(r["anomaly_score"] >= config.anomaly_threshold and r["canopy_pixels"] >= 15 for r in regions),
               "low_growth_count": sum(r["low_growth"] for r in regions), "region_count": len(regions),
               "processing_seconds": float(perf_counter() - started)}
    LOGGER.info("Analysed %s: %.1f%% canopy, %d candidate gaps, %.3fs", source_name,
                summary["canopy_coverage"], len(gaps), summary["processing_seconds"])
    return {"image": image, "mask": mask, "regions": regions, "gaps": gaps,
            "row_info": row_info, "summary": summary,
            "metadata": {"original_width": original_width, "original_height": original_height,
                         "processed_width": width, "processed_height": height,
                         "scale_x": scale_x, "scale_y": scale_y,
                         "source_name": str(source_name), "synthetic": bool(synthetic)},
            "config": config.to_dict(), "warnings": warnings}
