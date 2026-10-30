"""User-adjustable CPU baseline settings. Scores are heuristic, not probabilities."""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AnalysisConfig:
    max_dimension: int = 1600
    grid_rows: int = 8
    grid_cols: int = 10
    exg_threshold: float = 0.08
    saturation_min: int = 35
    hue_min: int = 22
    hue_max: int = 100
    min_component_area: int = 30
    morphology_size: int = 3
    gap_sensitivity: float = 1.5
    anomaly_threshold: float = 0.55
    low_growth_ratio: float = 0.55
    minimum_canopy_fraction: float = 0.02
    segmentation_mode: str = "combined"
    tile_size: int = 0

    def __post_init__(self):
        if not 64 <= self.max_dimension <= 4096:
            raise ValueError("Maximum analysis dimension must be 64–4096 pixels.")
        if not (1 <= self.grid_rows <= 30 and 1 <= self.grid_cols <= 30):
            raise ValueError("Grid dimensions must be 1–30.")
        if not (-1 <= self.exg_threshold <= 2):
            raise ValueError("ExG threshold must be between -1 and 2.")
        if not (0 <= self.hue_min < self.hue_max <= 179 and 0 <= self.saturation_min <= 255):
            raise ValueError("Invalid HSV thresholds.")
        if not (self.min_component_area >= 0 and 1 <= self.morphology_size <= 15):
            raise ValueError("Invalid morphology settings.")
        if not (0 < self.gap_sensitivity <= 5 and 0 <= self.anomaly_threshold <= 1):
            raise ValueError("Invalid gap or anomaly threshold.")
        if not (0 <= self.low_growth_ratio <= 1 and 0 <= self.minimum_canopy_fraction <= 1):
            raise ValueError("Coverage settings must be fractions between 0 and 1.")
        if self.segmentation_mode not in {"combined", "exg", "hsv", "otsu"}:
            raise ValueError("Unknown segmentation mode.")
        if self.tile_size != 0 and not 128 <= self.tile_size <= 4096:
            raise ValueError("Tile size must be zero (off) or 128–4096.")

    def to_dict(self):
        return asdict(self)
