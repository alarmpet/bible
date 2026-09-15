# -*- coding: utf-8 -*-
"""Build reviewer contact sheet for visual asset review."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def create_contact_sheet(build_dir: Path, output_file: Path | None = None, *, pilot_set: str | None = None) -> Path:
    images_dir = build_dir / "images"
    manifest_file = build_dir / "asset_manifest.json"

    if not manifest_file.exists():
        raise SystemExit(f"Manifest missing: {manifest_file}")

    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    assets = manifest_data.get("assets", [])
    if pilot_set:
        pilot_sets = manifest_data.get("pilot_sets", {})
        if pilot_set not in pilot_sets:
            raise ValueError(f"unknown pilot set: {pilot_set}")
        selected_ids = {str(scene_id) for scene_id in pilot_sets[pilot_set]}
        assets = [asset for asset in assets if str(asset.get("shot_id", "")) in selected_ids]
        assets.sort(key=lambda asset: pilot_sets[pilot_set].index(str(asset.get("shot_id", ""))))
    elif manifest_data.get("generation_scope") in {"pilot", "selected"}:
        expected_ids = {str(scene_id) for scene_id in manifest_data.get("expected_ids", [])}
        assets = [asset for asset in assets if str(asset.get("shot_id", "")) in expected_ids]

    if not output_file:
        output_file = build_dir / "contact_sheet.jpg"

    cols = 3
    rows = (len(assets) + cols - 1) // cols
    thumb_w, thumb_h = 480, 270

    sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), color=(20, 20, 25))
    draw = ImageDraw.Draw(sheet)

    for idx, item in enumerate(assets):
        img_name = item.get("file_path", "")
        img_path = images_dir / img_name
        r = idx // cols
        c = idx % cols
        x = c * thumb_w
        y = r * thumb_h

        if img_path.exists():
            try:
                with Image.open(img_path) as im:
                    thumb = im.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                    sheet.paste(thumb, (x, y))
            except Exception:
                draw.rectangle([x, y, x + thumb_w, y + thumb_h], fill=(80, 20, 20))
        else:
            draw.rectangle([x, y, x + thumb_w, y + thumb_h], fill=(40, 40, 40))

        label = f"[{item['shot_id']}] #{item['order']}"
        draw.text((x + 10, y + 10), label, fill=(255, 255, 255))

    output_file.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_file, format="JPEG", quality=90)
    print(f"✅ Contact sheet created: {output_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pilot-set", choices=["cold_open", "coverage"])
    args = parser.parse_args()
    create_contact_sheet(args.build, args.output, pilot_set=args.pilot_set)


if __name__ == "__main__":
    main()
