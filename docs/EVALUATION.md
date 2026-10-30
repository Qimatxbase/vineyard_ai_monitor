# Evaluation with independently supplied annotations

The application does not manufacture real-vineyard performance scores. The
synthetic demo can be evaluated against its known generated geometry, explicitly
as a software demonstration rather than field validation.

## Canopy or anomaly masks

Supply a binary grayscale PNG or TIFF with values `0` for background and `1` or
`255` for foreground. The annotation must refer to the **same image, crop and
resolution** as the prediction. RGB and palette images are rejected, including
pseudo-coloured reference imagery. No automatic colour thresholding or resizing
turns reference images into ground truth.

`segmentation_metrics(pred_mask, gt_mask)` returns IoU, Dice, pixel precision,
recall, F1, TP, FP, FN and TN. `evaluate_segmentation` wraps these as
`{"metrics": ..., "confusion": rgb_array}`. The confusion display uses green for
true positives, red for false positives, blue for false negatives and light grey
for true negatives. Empty masks still require nonempty image dimensions.

## Candidate gaps or annotated anomaly boxes

The JSON format is either a direct list or an object with a `boxes` key:

```json
{"boxes": [[40, 90, 72, 128], [110, 200, 149, 235]]}
```

Each box is `[x1, y1, x2, y2]` in image-relative pixels with half-open bounds,
nonnegative origin and positive width and height. Objects with `x1`, `y1`, `x2`,
`y2` keys are also accepted. The caller must use one consistent coordinate frame
for predictions and annotations. An empty list is a valid confirmed no-object
annotation; missing annotations must not be substituted with an empty list.

`detection_metrics` counts one-to-one matches whose IoU meets the chosen threshold
(default 0.5). It uses deterministic maximum-cardinality bipartite matching, so
duplicate predictions cannot reuse a ground-truth box and a greedy early choice
does not unnecessarily discard a valid match. These are fixed-threshold metrics,
not average precision or calibrated probabilities.

## Edge-case conventions

When both prediction and annotation have no foreground or boxes, IoU, Dice,
precision, recall and F1 are 1.0. When predictions are empty but ground truth is
positive, precision, recall and F1 are 0.0. With empty ground truth and positive
predictions, recall is 1.0 by convention while precision and F1 are 0.0. These
conventions are explicit and avoid NaN; report counts alongside ratios.

Processing time is measured separately by the pipeline. It depends on image
dimensions, machine and settings. A synthetic test result or one uploaded image
is not evidence of generalisation to other vineyards, seasons or camera systems.
