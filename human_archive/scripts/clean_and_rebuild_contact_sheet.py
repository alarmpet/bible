# -*- coding: utf-8 -*-
"""Clean orphan images not present in current 45-shot contract and rebuild contact sheet."""
import json
import sys
from pathlib import Path
from PIL import Image

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

c_path = Path("human_archive/runs/ep02_jang_huibin/source/shot_contract.json")
c_data = json.loads(c_path.read_text(encoding="utf-8"))
shot_ids = set(s["shot_id"] for s in c_data["shots"])
img_dir = Path("human_archive/runs/ep02_jang_huibin/full-v2-001/images")
all_imgs = list(img_dir.glob("*.jpg"))
orphans = [f for f in all_imgs if f.stem not in shot_ids]

print(f"Total contract shots: {len(shot_ids)}")
print(f"Total images in dir: {len(all_imgs)}")
print(f"Orphan images ({len(orphans)}): {[f.name for f in orphans]}")
for f in orphans:
    f.unlink()

# Rebuild contact sheet
valid_imgs = sorted([f for f in img_dir.glob("*.jpg") if f.stem in shot_ids])
print(f"Valid contract images count: {len(valid_imgs)}")

cols = 5
rows = (len(valid_imgs) + cols - 1) // cols
thumb_w, thumb_h = 384, 216
sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (15, 20, 25))
for i, im_p in enumerate(valid_imgs):
    with Image.open(im_p) as im:
        im_thumb = im.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        r_i = i // cols
        c_i = i % cols
        sheet.paste(im_thumb, (c_i * thumb_w, r_i * thumb_h))

sheet_path = Path("human_archive/runs/ep02_jang_huibin/full-v2-001/contact_sheet.jpg")
sheet.save(sheet_path, format="JPEG", quality=90)
print(f"✅ Rebuilt clean contact sheet: {sheet_path}")
