#!/usr/bin/env python3
"""Inspect a locally extracted dataset; optionally resize and write a manifest."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image

from src.data.dataset_loader import inspect_dataset, load_image
from src.data.preprocessing import prepare_image


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="Local folder of extracted RGB images")
    parser.add_argument("--output", type=Path, help="Write inspection.csv and manifest.json; resized PNGs if --resize is set")
    parser.add_argument("--resize", type=int, metavar="MAX_DIMENSION", help="Resize image longest edge (requires --output)")
    parser.add_argument("--limit", type=int, default=0, help="Process only the first N images (0 means all)")
    args = parser.parse_args(argv)
    if args.resize is not None and (args.output is None or args.resize < 1):
        parser.error("--resize requires --output and a positive pixel dimension")
    if args.limit < 0:
        parser.error("--limit must be nonnegative")
    try:
        frame = inspect_dataset(args.folder)
    except ValueError as exc:
        parser.error(str(exc))
    print(frame.to_string(index=False) if not frame.empty else "No supported images found.")
    print(f"\n{len(frame)} supported files; {int(frame['loadable'].sum())} decodable RGB inputs.")
    print("No annotation semantics, image pairings or georeferencing have been inferred.")
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        frame.to_csv(args.output / "inspection.csv", index=False)
        manifest = []
        usable = frame[frame["loadable"]]
        if args.limit:
            usable = usable.head(args.limit)
        for index, row in usable.iterrows():
            record = {"source": row["path"], "annotation": None, "synthetic": False}
            if args.resize:
                image, mapping = prepare_image(load_image(row["path"]), args.resize)
                # Sequence prefix avoids collisions between equally named files in subfolders.
                target = args.output / f"{index:05d}_{Path(row['path']).stem}.png"
                Image.fromarray(image).save(target)
                record.update(mapping, processed_path=str(target.resolve()))
            else:
                record.update(original_width=int(row["width"]), original_height=int(row["height"]))
            manifest.append(record)
        (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"Wrote {len(manifest)} manifest records to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
