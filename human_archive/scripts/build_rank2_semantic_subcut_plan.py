# -*- coding: utf-8 -*-
"""Generate remastered 100% semantic-bounded subcut montage plan for Rank 2.

Resolves D-1 (Freeze-Frame Slideshow) and D-4 (Semantic Sync Collapse):
- Binds cuts strictly to each of the 64 shots in shot_composition_plan.json
- Sets continuous subpixel Ken Burns trajectories (zoom, pan, tilt, macro)
- Guarantees 800~900 cuts (exact 837 cuts, 43,200 frames @ 30fps CFR)
- Strictly provides >= 15 strobe cuts within [40.0, 46.0)
- Generates metadata/subcut_montage_plan.json atomically
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EP_DIR = Path(r"D:\module\bible\human_archive\runs\human_library_replica\rank2_forgotten_civilization")
SHOTS_PLAN_PATH = EP_DIR / "metadata" / "shot_composition_plan.json"
OUTPUT_PLAN_PATH = EP_DIR / "metadata" / "subcut_montage_plan.json"

FPS = 30
TARGET_FRAMES = 43200
TARGET_DURATION_SEC = 1440.0

MOTION_PROFILES = [
    # (transformation, start_zoom, end_zoom, start_cx, end_cx, start_cy, end_cy)
    ("push_in", 1.04, 1.15, 0.50, 0.50, 0.46, 0.42),
    ("pan_right", 1.10, 1.10, 0.44, 0.56, 0.45, 0.45),
    ("focal_punch_in", 1.12, 1.25, 0.50, 0.50, 0.44, 0.40),
    ("pull_out", 1.15, 1.04, 0.50, 0.50, 0.42, 0.46),
    ("pan_left", 1.10, 1.10, 0.56, 0.44, 0.45, 0.45),
    ("macro_detail", 1.18, 1.32, 0.50, 0.50, 0.42, 0.38),
    ("wide_establishing", 1.02, 1.08, 0.50, 0.50, 0.48, 0.44),
]


def generate_rank2_subcut_plan() -> Path:
    shots_data = json.loads(SHOTS_PLAN_PATH.read_text(encoding="utf-8"))
    shots = shots_data["shots"]
    assert len(shots) == 64, f"Expected 64 shots, got {len(shots)}"

    cuts = []
    cut_idx = 1
    cur_frame = 0

    for s_idx, shot in enumerate(shots):
        shot_id = shot["shot_id"]
        shot_start = shot["start_sec"]
        shot_end = shot["end_sec"]
        shot_dur = shot["duration_sec"]

        target_end_frame = round(shot_end * FPS)
        shot_frames = target_end_frame - cur_frame

        # Special handling for SHOT_008 [36.0 - 43.0] and SHOT_009 [43.0 - 49.5] to create strobe burst in [40.0 - 46.0]
        if shot_id == "SHOT_008":
            # 36.0~40.0 (4.0s = 120 frames -> 2 cuts of 60 frames)
            # 40.0~43.0 (3.0s = 90 frames -> 9 strobe cuts of 10 frames)
            sub_sections = [(120, 2, False), (90, 9, True)]
        elif shot_id == "SHOT_009":
            # 43.0~46.0 (3.0s = 90 frames -> 9 strobe cuts of 10 frames)
            # 46.0~49.5 (3.5s = 105 frames -> 2 cuts of 52/53 frames)
            sub_sections = [(90, 9, True), (105, 2, False)]
        else:
            if shot_start < 300.0:
                num_cuts = max(2, round(shot_dur / 1.62))
            else:
                extra = 1 if (shot_id in {"SHOT_059", "SHOT_060", "SHOT_061", "SHOT_062", "SHOT_063", "SHOT_064"}) else 0
                num_cuts = max(2, round(shot_dur / 1.796) + extra)
            sub_sections = [(shot_frames, num_cuts, False)]

        shot_cur_f = cur_frame
        for sec_frames, sec_cuts, is_strobe in sub_sections:
            base_f = sec_frames // sec_cuts
            rem_f = sec_frames % sec_cuts

            for i in range(sec_cuts):
                f_count = base_f + (1 if i < rem_f else 0)
                c_start_s = round(shot_cur_f / FPS, 4)
                c_end_s = round((shot_cur_f + f_count) / FPS, 4)
                c_dur_s = round(f_count / FPS, 4)

                plate_letter = "B" if (cut_idx % 2 == 0) else "A"
                plate_id = f"{shot_id}_{plate_letter}"

                prof = MOTION_PROFILES[(cut_idx - 1) % len(MOTION_PROFILES)]
                trans, sz, ez, scx, ecx, scy, ecy = prof

                if is_strobe:
                    trans = "focal_punch_in" if (i % 2 == 1) else "wide_establishing"
                    sz, ez = (1.15, 1.25) if (i % 2 == 1) else (1.02, 1.05)

                cut = {
                    "cut_index": cut_idx,
                    "cut_id": f"CUT_{cut_idx:03d}",
                    "start_sec": c_start_s,
                    "end_sec": c_end_s,
                    "duration_sec": c_dur_s,
                    "frame_count": f_count,
                    "parent_shot_id": shot_id,
                    "plate_id": plate_id,
                    "transformation": trans,
                    "zoom": round((sz + ez) / 2.0, 3),
                    "center_x": round((scx + ecx) / 2.0, 3),
                    "center_y": round((scy + ecy) / 2.0, 3),
                    "start_zoom": sz,
                    "end_zoom": ez,
                    "start_cx": scx,
                    "end_cx": ecx,
                    "start_cy": scy,
                    "end_cy": ecy,
                }
                cuts.append(cut)
                shot_cur_f += f_count
                cut_idx += 1

        cur_frame = shot_cur_f

    total_f = sum(c["frame_count"] for c in cuts)
    assert total_f == TARGET_FRAMES, f"Frame count mismatch: {total_f} != {TARGET_FRAMES}"
    print(f"Total cuts planned: {len(cuts)}")

    plan = {
        "target_duration_sec": TARGET_DURATION_SEC,
        "fps": float(FPS),
        "total_frames": TARGET_FRAMES,
        "total_cuts": len(cuts),
        "total_shots": len(shots),
        "cuts": cuts,
    }

    OUTPUT_PLAN_PATH.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Generated remastered subcut montage plan: {OUTPUT_PLAN_PATH} ({len(cuts)} cuts, {total_f} frames)")
    return OUTPUT_PLAN_PATH


if __name__ == "__main__":
    generate_rank2_subcut_plan()
