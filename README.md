# Vineyard AI Monitor

A working CPU-only hackathon MVP that turns overhead RGB drone imagery into a vineyard inspection map.

**Upload drone image → segment visible canopy → find row-supported gaps and unusual regions → inspect the health map → export results.**

## Run locally

Requires Python **3.11+**. From this workspace:

```bash
cd hackathon/vineyard_ai_monitor  # From the UTS workspace
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, usually <http://localhost:8501>.
Create the virtual environment after cloning or moving this project.
For another machine, change the first command to its project path.

With `uv`, the equivalent setup is:

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements-lock.txt
.venv/bin/streamlit run app.py
```

`requirements.txt` declares supported dependency ranges; `requirements-lock.txt`
records the versions verified in this checkout. No GPU, model download,
credentials, paid services or external APIs are required. Usage telemetry is
disabled. Images and results remain local to the running app.

## Try the complete workflow

1. On **Overview**, click **Try the synthetic vineyard demo**. The app analyses a deterministic, generated vineyard image immediately.
2. In **Vineyard Analysis**, inspect the actual binary mask, vegetation overlay, visual anomaly regions and possible gaps. Change settings and click **Analyse Vineyard** to rerun.
3. Open **Vineyard Health Map**. Pan/zoom, hover over region centres, toggle overlays, select a region for a crop, and review the inspection queue and coverage/anomaly charts.
4. Expand **Download analysis results** for CSV, JSON, original-size canopy mask PNG, annotated image, health map PNG or a complete ZIP.
5. On **Evaluation**, enable **Use synthetic demonstration annotations**, then evaluate canopy, gaps or visual anomalies. Scores describe fabricated shapes only. For real images, supply independent, aligned annotations.

All generated-demo views are labelled synthetic. The exact bundled sample is
recognised by its file-content hash when uploaded or loaded from a folder.
For other uploaded images, the user is responsible for provenance;
the app cannot reliably infer whether arbitrary image bytes are synthetic.
The included synthetic fixtures must not be presented as field measurements.

See [the three-minute demo script and team roles](docs/DEMO.md).

## Use real RGB images

Upload JPG/JPEG, PNG or TIF/TIFF files, or choose **Local folder**, enter the path,
click **Scan folder**, and select images. Relative and absolute paths work.
Batch analysis supports up to 12 images per run. Choose the active image to
inspect its results; the batch ZIP includes a summary and a result ZIP per image.
Local folders are read from the machine hosting Streamlit, not a remote browser.

Images are limited to 100 MB in the dashboard and 40 million pixels at decoding.
Resize or crop larger images locally. EXIF orientation is applied. Original
coordinates mean pixels in the oriented image. The first TIFF page is used;
16-bit monochrome values receive a display conversion, not thermal calibration.
Keep thermal and pseudo-colour images out of the selected RGB folder.

The maximum analysis side defaults to 1600 pixels. Optional tiled segmentation
operates at this analysis resolution, retains one global Otsu threshold and
performs component/morphology filtering after tile assembly to avoid seams.
It is not an out-of-core full-resolution mosaic processor.

### Dataset

Source: [Fevgas et al., Zenodo record 13862443](https://zenodo.org/records/13862443).
The record contains 375 images in each of RGB, thermal and pseudo-colour
collections. We inspected the actual ZIP central directories using small HTTP
range requests; no complete archives were downloaded.

Observed structures include `RGB/DJI_0182_W.JPG`, `TIR/DJI_0183_T.JPG`, and
`Pseudo-coloring RGBs/1.jpg`. Different filename schemes and the described
thermal-field-of-view crops do not establish direct RGB correspondence.
No binary masks or pairing manifest were observed in the archive listings.
Pseudo-colour images are reference material, not automatically independent
ground truth. The application performs RGB-only analysis.

Manually extract a manageable RGB subset, then inspect it:

```bash
python scripts/prepare_dataset.py /path/to/extracted/RGB
python scripts/prepare_dataset.py /path/to/extracted/RGB \
  --output data/processed/rgb --resize 1600 --limit 10
```

The preparation command writes actual dimensions, decoding errors and optional
resized images with coordinate metadata. It does not infer labels or pairings.
See [dataset inspection details](docs/DATASET.md).

## Implemented analysis

| Component | Working baseline |
| --- | --- |
| Canopy segmentation | Excess Green `(2G-R-B)/255`, HSV thresholding, optional global Otsu, morphological filtering and connected-component removal. Adjustable parameters. |
| Row and gap detection | Repeated parallel row-band estimation over orientations; unusually wide interior canopy interruptions only. Abstains on weak/insufficient row structure. |
| Coverage and growth | Whole-image and grid-region canopy percentages, relative neighbourhood coverage, growth ratio and local coefficient of variation. |
| Visual anomalies | Relative greenness deficit, yellow-canopy fraction and regional coverage deficit. Deterministic scores calculated from the image. |
| Inspection map | Actual image with coloured region overlays, black gap markers, hover statistics, image-pixel axes, zoom and selected-region crops. |
| Exports | Actual regional CSV, structured JSON with parameters/provenance, binary mask, annotated image, health-map PNG and batch ZIP. |
| Evaluation | Strict binary annotation ingestion; canopy/anomaly pixel IoU, Dice, precision/recall/F1; gap box precision/recall/F1; false-positive/negative overlays and JSON reports. |

Anomaly score:

```text
0.55 × relative greenness deficit
+ 0.30 × scaled yellow-canopy fraction
+ 0.15 × relative coverage deficit
```

Greenness uses the median across canopy-bearing regions and a median absolute
deviation reference. Coverage compares suitable neighbouring canopy regions,
falling back to the global median. A score is an inspection cue, not a
calibrated probability. Small or empty regions carry uncertainty.

Classification uses explicit precedence:

1. **BLACK — Possible Canopy Gap:** a supported gap centre lies in the region.
2. **RED — Potential Stress / Inspect:** visible canopy and anomaly score ≥ threshold (default 0.55).
3. **YELLOW — Low Growth / Monitor:** relative coverage below the configured ratio (default 0.55).
4. **GREEN — Normal / Healthy-looking:** adequate visible canopy without the above flags.

Insufficient-canopy regions receive YELLOW with an uncertainty issue and a
faint/neutral map treatment. They are excluded from the low-growth count.
Candidate-gap boxes remain distinct from the grid cell containing their centre.

### Coordinates and exports

All coordinates are **image-relative**, with top-left origin, x rightwards and
y downwards. Boxes are half-open `[x1,y1,x2,y2)`. No GPS coordinates are invented.

Region/gap fields `x1`…`y2` use processed pixels. `original_x1`…`original_y2`
map to original, EXIF-oriented pixels; metadata includes both dimensions and
`scale_x/y = original / processed`. The canopy PNG is nearest-neighbour
rescaled to original dimensions. Annotated PNGs use processed dimensions;
the map PNG adds a provenance/legend footer. Rescaling preserves coordinate
correspondence, not full-resolution segmentation detail.

## Evaluation and checks

```bash
python -m pytest -q
```

Tests exercise actual segmentation and pipeline behaviour, rotated row gaps,
unsupported structures, empty inputs, tiling, coordinate mapping, ingestion,
strict ground truth, duplicate box matches, export contents and dashboard
interactions using Streamlit AppTest.

Use binary grayscale PNG/TIFF annotations at original oriented dimensions.
Colour/palette pseudo-colour references and mismatched shapes are rejected.
Gap annotations use `{"boxes": [[x1,y1,x2,y2], ...]}` in original pixels.
Visual-anomaly evaluation compares RED region cells intersected with segmented
canopy against a supplied binary visual-anomaly mask. It reports pixel metrics,
not diagnostic accuracy. No scores are generated without supplied annotations
or an explicitly enabled synthetic fixture.

For empty foreground sets, both sets empty scores 1.0; absent ground-truth
positives gives recall 1.0 while false positives reduce precision/F1.
See [evaluation conventions and formats](docs/EVALUATION.md).

## Project structure and ownership

```text
app.py                         Dashboard entry point
config.py                      Validated analysis settings
pages/                         Overview, analysis, map, evaluation, about
src/data/                      Image loading, preprocessing, synthetic fixture
src/vision/                    Segmentation, rows, gaps, coverage, anomalies, pipeline
src/mapping/                   Interactive map and PNG overlays
src/evaluation/                Annotation loading, metrics, error visualisation
src/utils/export.py            CSV/JSON/PNG/ZIP exports
src/dashboard.py               Shared cached analysis and dashboard helpers
scripts/prepare_dataset.py     Local dataset inspection and resizing
tests/                         Component, integration and UI tests
data/sample/                   Clearly labelled synthetic demo and annotations
docs/                          Dataset findings, evaluation guide, demo script
```

Person 1 owns business/product and presentation; Person 2 owns `src/vision`;
Person 3 owns `src/evaluation` and testing; Person 4 owns data, mapping,
dashboard integration and exports. Modules expose reusable Python functions,
including `src.vision.pipeline.analyze_image`.

## Limits and experimental features

The end-to-end baseline is implemented. Its agricultural interpretation remains
experimental and **has not been validated on independently labelled real
vineyards**. RGB thresholds can include weeds/trees, miss senescent canopy, or
react to illumination/shadows. Row detection assumes roughly straight repeated
rows; curved rows, perspective and irregular planting can invalidate it.
Fixed grids reflect planting geometry as well as growth.

Visible canopy coverage is not biomass. Colour anomalies do not diagnose
disease or prove water stress. A gap does not confirm a missing vine. Field
inspection and independent annotations are needed to establish useful accuracy
or economic benefit. All provided demonstration images are synthetic.

Trainable vine-specific models, thermal registration/comparison, genuine GPS
mapping and out-of-core mosaics are future extensions. They are not required
or represented as working features in this MVP.
