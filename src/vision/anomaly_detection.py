"""Relative RGB appearance scores, without disease or water-stress diagnosis."""
import numpy as np

from config import AnalysisConfig


def score_anomalies(regions: list[dict], gaps: list[dict], config: AnalysisConfig) -> list[dict]:
    suitable = [r for r in regions if r["canopy_coverage"] >= config.minimum_canopy_fraction * 100 and r["mean_greenness"] is not None]
    greenness = np.array([r["mean_greenness"] for r in suitable])
    if len(greenness):
        reference = float(np.median(greenness))
        spread = max(0.05, float(np.median(np.abs(greenness - reference)) * 1.4826))
    else:
        reference, spread = 0.0, 0.05
    for region in regions:
        issues = []
        enough = region["canopy_coverage"] >= config.minimum_canopy_fraction * 100 and region["canopy_pixels"] >= 15
        if enough:
            relative = float(np.clip((reference - region["mean_greenness"]) / (3 * spread), 0, 1))
            yellow = float(np.clip((region["yellow_fraction"] or 0) / 0.65, 0, 1))
            sparse = float(np.clip(1 - region["growth_ratio"], 0, 1))
            # Fixed transparent weights; score is not a calibrated likelihood.
            score = 0.55 * relative + 0.30 * yellow + 0.15 * sparse
            if relative >= 0.4:
                issues.append("Lower relative canopy greenness")
            if yellow >= 0.35:
                issues.append("Yellowing / unusual canopy colour")
        else:
            score = 0.0
        low_growth = (enough and region["neighbour_canopy_reference"] >= config.minimum_canopy_fraction * 100
                      and region["growth_ratio"] < config.low_growth_ratio)
        matching_gaps = [g for g in gaps if region["x1"] <= g["center_x"] < region["x2"] and region["y1"] <= g["center_y"] < region["y2"]]
        category = "GREEN"
        if low_growth:
            category = "YELLOW"
            issues.append("Low canopy coverage relative to neighbouring regions")
        if enough and score >= config.anomaly_threshold:
            category = "RED"
            issues.append("Potential Stress / Requires Inspection")
        if matching_gaps:
            category = "BLACK"
            issues.append("Possible Canopy Gap")
        if not enough and not low_growth and not matching_gaps:
            # Green means normal looking canopy only when actual canopy is visible.
            category = "YELLOW"
            issues.append("Insufficient visible canopy; inspect image context")
        region.update({"anomaly_score": float(score), "category": category, "issues": issues,
                       "colour_reference_available": len(suitable) >= 3,
                       "has_canopy": bool(enough),
                       "low_growth": bool(low_growth)})
    return regions
