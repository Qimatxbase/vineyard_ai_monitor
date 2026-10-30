# Data ingestion and source inspection

The application runs entirely on local RGB inputs. There is no network request,
automatic dataset download, thermal sensor input or model download at runtime.

## Zenodo source

Source: [Aerial RGB and Thermal Infrared (TIR) Images of Vineyards and
Pseudo-coloring RGB Images of the Plant's Stressed Areas](https://zenodo.org/records/13862443),
DOI [10.5281/zenodo.13862443](https://doi.org/10.5281/zenodo.13862443).
Creators: Georgios Fevgas, Thomas Lagkas, Vasileios Argyriou and Panagiotis
Sarigiannidis. Published September 30, 2024, version v1.

The record describes 375 visible RGB photographs, 375 thermal infrared images,
and 375 pseudo-colour images depicting stress areas. The pseudo-colour images
are described as aligned/cropped to the thermal field of view. This does not
establish alignment with the full-resolution RGB photographs or independent
ground-truth validity.

The record and ZIP central directories were inspected on October 28, 2026.
Only HTTP headers and a 65,536-byte suffix range per archive were read;
the multi-gigabyte archives were not downloaded. All three responses honoured
the requested byte range with HTTP 206. Each central directory was contained
in that suffix, and contained 376 entries: one folder and 375 JPEG files.

| Archive | Record size | Observed internal folder and filenames |
| --- | --- | --- |
| `RGB.zip` | 7.7 GB; HTTP length 7,657,976,421 bytes | `RGB/DJI_0182_W.JPG`, `RGB/DJI_0184_W.JPG`, …, `RGB/DJI_0940_W.JPG` |
| `TIR.zip` | 373.4 MB | `TIR/DJI_0183_T.JPG`, `TIR/DJI_0185_T.JPG`, …, `TIR/DJI_0941_T.JPG` |
| `Pseudo-coloring RGB.zip` | 1.5 GB | `Pseudo-coloring RGBs/1.jpg`, `10.jpg`, `100.jpg`, … (375 numbered JPEGs) |

The displayed examples do not imply a continuous filename sequence. No
binary segmentation masks, object annotation files, pairing manifest, camera
calibration, or geospatial sidecars were observed in these archive listings.
JPEG pixel data and embedded metadata were not inspected in this metadata-only
review. Consequently, this application never auto-pairs the three collections,
interprets pseudo-colour values as definitive labels, or invents GPS positions.

For use, manually obtain/extract the RGB archive or a manageable subset, then
select the actual RGB folder in the dashboard. Keep thermal/pseudo-colour
collections separate to prevent accidentally analysing them as ordinary RGB
drone photographs. Review the record's usage terms before redistributing data.

## Inspect your actual local folder

From the project root, after installing requirements:

```bash
python scripts/prepare_dataset.py /absolute/path/to/extracted/RGB
python scripts/prepare_dataset.py /absolute/path/to/extracted/RGB \
  --output data/processed/rgb --resize 1600 --limit 10
```

The first command prints actual supported image paths, dimensions, format,
colour mode and decoding errors. The second also writes `inspection.csv`,
`manifest.json`, and resized PNGs. The manifest records original/processed
dimensions and coordinate scaling. It leaves annotations explicitly unset.
No image association is inferred from directory ordering or similar names.

## Image interpretation

- JPG/JPEG, PNG, TIF and TIFF are supported, case-insensitively.
- EXIF orientation is applied before processing. Original pixel coordinates
  throughout the application refer to this oriented image.
- Inputs larger than 40 million pixels are rejected before decoding. Resize
  or crop such inputs locally; downsampling is then applied without upsampling.
- Transparent images are composited on white. Grayscale inputs are expanded
  to RGB channels, but cannot provide useful RGB colour discrimination.
- The first page of a multipage TIFF is used. Unsigned 16-bit monochrome values
  are mapped from 0–65535 to 0–255. This is display conversion, not temperature
  extraction. Thermal radiometric calibration and multispectral bands are not
  supported.
- Pixel coordinates use half-open boxes `[x1,y1,x2,y2)`. Coordinate mapping uses
  `original_x = processed_x * scale_x` and the corresponding y equation, with
  bounds rounded/clipped by the analysis pipeline.
- `iter_tiles` yields `((x1,y1,x2,y2), tile)`. Border tiles can be smaller, and
  coordinates refer to the supplied image. Overlapping tiles require merging.

## Synthetic demonstration

`src/data/synthetic.py` deterministically draws an overhead vineyard image
with parallel canopy rows, two deliberate gaps, a yellow canopy patch and
areas with smaller canopy shapes. Seed 7 is the default. Assets are included in
`data/sample` so no downloaded sample is needed.

The canopy/anomaly masks record the exact fabricated drawing shapes. Gap
boxes describe the deliberately removed sections. These fixtures test software
and demonstrate the workflow; evaluations against them do not measure real
vineyard performance. They are not training labels for Zenodo data.
