# -*- coding: utf-8 -*-
"""Generate K-Webtoon prompt inventory for EP03 Maecheon Yarok."""
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

contract_path = Path("human_archive/runs/ep03_maecheon/source/shot_contract.json")
contract_data = json.loads(contract_path.read_text(encoding="utf-8"))
shots = contract_data.get("shots", [])

prompts_list = []
text_lines = []

for idx, s in enumerate(shots, 1):
    shot_id = s["shot_id"]
    order = s["order"]
    vis = s.get("visual", {})
    subject = vis.get("subject", "Historical scene")
    place = vis.get("place", "Gurye Seojae Study")

    prompt = (
        f"Masterpiece Korean historical webtoon style manhwa illustration: {subject}, located at {place} during 1864-1910 Late Joseon Dynasty. "
        f"Fine delicate ink contour line work, rich Hanji color wash, dramatic chiaroscuro candle lighting with deep obsidian shadows and warm amber rim light, "
        f"volumetric dust particles, 8k resolution, cinematic anime keyframe, trending on Webtoon, highly detailed"
    )

    prompts_list.append({
        "shot_id": shot_id,
        "order": order,
        "filename": f"{shot_id}.jpg",
        "subject": subject,
        "place": place,
        "prompt": prompt
    })

    text_lines.append(f"[{idx:02d}] {shot_id}.jpg ({subject[:30]}...)\n{prompt}\n")

out_json = Path("human_archive/runs/ep03_maecheon/source/flow_prompts_45shots.json")
out_txt = Path("human_archive/runs/ep03_maecheon/source/flow_prompts_45shots.txt")

out_json.write_text(json.dumps(prompts_list, indent=2, ensure_ascii=False), encoding="utf-8")
out_txt.write_text("\n".join(text_lines), encoding="utf-8")

print(f"✅ Generated {len(prompts_list)} K-Webtoon prompts to {out_json} and {out_txt}")
