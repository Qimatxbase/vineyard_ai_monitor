# Synthetic demonstration fixtures

All assets here are fabricated by `src/data/synthetic.py`, seed 7. No real
vineyard photograph is included. The drawing includes parallel rows, deliberate
canopy gaps, smaller canopy shapes and a yellow patch.

- `synthetic_vineyard.png`: RGB drawing for analysis.
- `synthetic_canopy_mask.png`: exact drawn canopy, binary PNG (255 = canopy).
- `synthetic_anomaly_mask.png`: exact fabricated yellow patch (255 = patch).
- `synthetic_gap_boxes.json`: deliberately removed canopy boxes in original
  image-relative pixels, `[x1,y1,x2,y2)`.
- `metadata.json`: explicit synthetic provenance.

Use the RGB drawing as an input, and the masks only in evaluation. Do not treat
this folder as a collection of ordinary drone images for batch analysis.
Metrics against fabricated labels verify software only, never field accuracy.
