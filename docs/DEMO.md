# Three-minute hackathon demonstration

**Pitch:** Vineyard AI Monitor turns an overhead RGB drone image into an
inspection queue: visible canopy, unusual canopy regions and possible gaps,
shown together on a map a vineyard manager can explore.

## Before presenting

From the project directory, activate the installed Python environment and run:

```bash
source .venv/bin/activate
streamlit run app.py
```

Open the project overview and introduce **Who we are** and **What we solve**.
Click the centred **Enter our project** button to open **Dashboard**; no login
is needed. Use the top bar to move between analysis, the health map,
Drone Connect and evaluation, or return with **Overview**. The built-in [synthetic vineyard image](../data/sample/synthetic_vineyard.png)
works without downloading a dataset, credentials, a GPU or internet access.
Check that the browser shows the synthetic provenance notice.

## Live walkthrough

| Time | Show | Say |
| --- | --- | --- |
| 0:00–0:25 | Dashboard, coverage and inspection priorities | “A drone image covers many rows. Our goal is to help a manager decide which areas deserve a closer inspection. This dashboard uses a generated vineyard illustration, with deliberately introduced gaps and yellow canopy.” |
| 0:25–1:00 | Click **Run synthetic analysis**, or open **Analysis → Synthetic demo → Analyse Vineyard** | “The CPU pipeline segments visible vegetation, compares regional coverage and colour, estimates row structure, and searches for gaps within supported rows. These displayed results are calculated from the image.” |
| 1:00–1:35 | Canopy segmentation, anomaly and possible-gap tabs | “The mask shows which pixels the baseline regards as canopy. Yellow-looking canopy can differ from nearby regions. Black boxes are candidate gaps; a bare inter-row strip alone is not sufficient evidence of a missing plant.” |
| 1:35–2:15 | **Vineyard Health Map**; toggle overlays, zoom, hover, select a region | “Green means healthy-looking under these rules, yellow means monitor low growth, red means inspect a visual anomaly, and black marks a possible gap. We can review a region's coverage, anomaly score and original pixel coordinates, then work through the inspection queue.” |
| 2:15–2:35 | Download controls | “The team can export the actual regional CSV, structured JSON, canopy mask, annotated image and inspection map. Coordinates belong to the image; this baseline does not invent GPS locations.” |
| 2:35–3:00 | **Evaluation**, then close with the map | “Evaluation needs appropriate ground truth. Synthetic labels check the software workflow; field accuracy remains unmeasured. RGB colour cannot diagnose disease or establish water stress. Our practical output is a prioritised set of places for a farmer to inspect.” |

If a real RGB image is available, use **Upload images** or scan its local RGB
folder. Show the row-structure notice: gap analysis may abstain when rows are
unclear. Do not promise that a new image will produce any particular flag.

For the optional **Drone Connect** demonstration, show the simulated connection,
preflight checks and inspection progress, then capture a generated frame and
open its health map. All telemetry and drone states are synthetic. No drone is
contacted and no real flight command is sent. The captured image goes through
the normal RGB analysis pipeline; its results retain synthetic provenance.
Use **Discover demo drone → Connect demo drone → Run preflight check → Start
demo inspection → Capture demo frame → Open captured health map**. To show a
blocked preflight, reconnect with the **Low battery** or **Weak signal** scenario.

## Four-person delivery

| Team member | Responsibility | Demonstration contribution |
| --- | --- | --- |
| Person 1 — Business & Product | Farmer problem, use cases, value proposition and presentation | Introduce the inspection problem and explain how a manager would use the queue. |
| Person 2 — Core AI | Canopy segmentation, row structure, gap detection, regional anomaly rules and pipeline | Explain one mask and one candidate finding, including uncertainty. |
| Person 3 — Evaluation | Ground-truth handling, metrics, tests and error analysis | Distinguish software tests from field validation and show evaluation requirements. |
| Person 4 — Data & Dashboard | Image ingestion, resizing, map, UI and exports | Run the live workflow, inspect a region and download results. |

## Value and honest boundaries

- Intended value: organise large visual inputs into a reviewable inspection
  queue. Time savings and economic benefit require a future field study.
- The baseline uses configurable image-processing rules. Anomaly scores are
  relative screening scores, not calibrated probabilities.
- The mask detects visible vegetation, which can include weeds or neighbouring
  trees. Sparse, shaded, yellow or brown canopy can be missed.
- Coverage describes visible projected canopy, not biomass. Gap candidates
  are not confirmed missing plants, and colour anomalies are not diagnoses.
- Dataset pseudo-colour images are reference material, not automatically
  independently validated segmentation labels. The RGB pipeline uses no
  thermal measurements.

See [dataset inspection and input conventions](DATASET.md),
[evaluation conventions](EVALUATION.md), and
[synthetic fixture provenance](../data/sample/README.md).
