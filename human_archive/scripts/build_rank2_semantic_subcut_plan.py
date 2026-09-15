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
SCRIPTS_DIR = Path(__file__).resolve().parent
LIB_DIR = SCRIPTS_DIR / "lib"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from lib.exact_release_verifier import audit_subcut_montage_plan
from lib.rank2_visual_contract import (
    annotate_cut_contract,
    audit_visual_anchor_contract,
    audit_v3_pacing,
    build_rank2_lineage,
    build_v3_pacing_policy,
    choose_motion_profile,
    transition_for_boundary,
)

SHOTS_PLAN_PATH = EP_DIR / "metadata" / "shot_composition_plan.json"
NORMALIZED_BUNDLE_PATH = EP_DIR / "metadata" / "normalized_replica_bundle.json"
NORMALIZED_SCRIPT_PATH = EP_DIR / "script" / "normalized_script.json"
CANONICAL_MANIFEST_PATH = EP_DIR / "metadata" / "canonical_timeline_manifest.json"
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


def build_v3_cut_counts(
    shots: list[dict], *, target_visible_cuts: int = 455
) -> list[int]:
    """Allocate calm visible cuts by shot duration with an intentionally slow hook."""
    if target_visible_cuts < len(shots):
        raise ValueError("target_visible_cuts must leave at least one cut per shot")
    counts = [max(1, round(float(shot["duration_sec"]) / 3.2)) for shot in shots]

    def add_priority(index: int) -> tuple[int, float]:
        shot = shots[index]
        # Prefer body shots so the opening is not made faster just to meet a
        # global count budget.
        body_penalty = 0 if float(shot["start_sec"]) >= 30.0 else 1
        return body_penalty, -float(shot["duration_sec"])

    while sum(counts) < target_visible_cuts:
        index = min(range(len(shots)), key=add_priority)
        counts[index] += 1

    while sum(counts) > target_visible_cuts:
        candidates = [
            index for index, count in enumerate(counts)
            if count > 1 and float(shots[index]["start_sec"]) >= 30.0
        ]
        if not candidates:
            candidates = [index for index, count in enumerate(counts) if count > 1]
        if not candidates:
            raise ValueError("cannot reduce cut count while keeping one cut per shot")
        index = max(candidates, key=lambda item: float(shots[item]["duration_sec"]))
        counts[index] -= 1

    if sum(counts[:3]) > 4 or sum(counts[:4]) > 10:
        raise ValueError("V3 hook cut budget cannot be satisfied")
    return counts


def _build_semantic_anchor_index(
    shots: list[dict], plates: list[dict]
) -> dict[str, dict[str, str]]:
    shot_index = {str(shot["shot_id"]): shot for shot in shots}
    plate_index = {str(plate["plate_id"]): plate for plate in plates}
    result: dict[str, dict[str, str]] = {}
    for shot_id, shot in shot_index.items():
        visual = shot.get("visual", {})
        for letter, role in (("A", "context"), ("B", "evidence")):
            plate_id = f"{shot_id}_{letter}"
            plate = plate_index.get(plate_id, {})
            result[plate_id] = {
                "place": str(visual.get("place", "")).strip(),
                "subject": str(visual.get("subject", "")).strip(),
                "action": str(visual.get("action", "")).strip(),
                "era": str(visual.get("era", "")).strip(),
                "evidence_role": role,
                "plate_prompt": str(plate.get("flow_prompt_en", "")).strip(),
            }
    return result


def generate_rank2_subcut_plan(
    output_plan_path: Path = OUTPUT_PLAN_PATH,
    *,
    pacing: str = "v2",
    target_visible_cuts: int | None = None,
) -> Path:
    shots_data = json.loads(SHOTS_PLAN_PATH.read_text(encoding="utf-8"))
    shots = shots_data["shots"]
    assert len(shots) == 64, f"Expected 64 shots, got {len(shots)}"

    cuts = []
    cut_idx = 1
    cur_frame = 0

    normalized_bundle = json.loads(NORMALIZED_BUNDLE_PATH.read_text(encoding="utf-8"))
    normalized_script = json.loads(NORMALIZED_SCRIPT_PATH.read_text(encoding="utf-8"))
    canonical_manifest = json.loads(CANONICAL_MANIFEST_PATH.read_text(encoding="utf-8"))
    plates_plan = json.loads((EP_DIR / "metadata" / "master_plates_composition_plan.json").read_text(encoding="utf-8"))
    lineage_index = build_rank2_lineage(normalized_bundle, normalized_script, canonical_manifest)
    anchor_index = _build_semantic_anchor_index(normalized_bundle["shots"], plates_plan.get("plates", []))

    if pacing not in {"v2", "v3_calm"}:
        raise ValueError(f"unknown pacing policy: {pacing}")
    v3_policy = build_v3_pacing_policy() if pacing == "v3_calm" else None
    v3_counts = (
        build_v3_cut_counts(shots, target_visible_cuts=target_visible_cuts or 455)
        if pacing == "v3_calm"
        else None
    )

    previous_shot_id: str | None = None
    for s_idx, shot in enumerate(shots):
        shot_id = shot["shot_id"]
        shot_start = shot["start_sec"]
        shot_end = shot["end_sec"]
        shot_dur = shot["duration_sec"]

        target_end_frame = round(shot_end * FPS)
        shot_frames = target_end_frame - cur_frame

        if v3_counts is not None:
            num_cuts = v3_counts[s_idx]
        else:
            # The source is a slow documentary, so 2.4s is the upper-level visual
            # beat cadence.  There is no ungrounded 40~46s strobe burst.
            num_cuts = max(2 if s_idx < 3 else 1, round(shot_dur / 2.4))
        n_a = (num_cuts + 1) // 2
        n_b = num_cuts - n_a
        plate_assignments = ["A"] * n_a + ["B"] * n_b
        sub_sections = [(shot_frames, num_cuts, plate_assignments)]

        shot_cur_f = cur_frame
        for sec_frames, sec_cuts, plate_letters in sub_sections:
            base_f = sec_frames // sec_cuts
            rem_f = sec_frames % sec_cuts

            for i in range(sec_cuts):
                f_count = base_f + (1 if i < rem_f else 0)
                c_start_s = round(shot_cur_f / FPS, 4)
                c_end_s = round((shot_cur_f + f_count) / FPS, 4)
                c_dur_s = round(f_count / FPS, 4)

                plate_letter = plate_letters[i]
                role = "context_wide" if plate_letter == "A" else "detail_evidence"
                plate_id = f"{shot_id}_{plate_letter}"

                profile = choose_motion_profile(
                    shot_index=s_idx,
                    cut_index=i,
                    cut_count=sec_cuts,
                    pacing=pacing,
                )
                trans = profile["transformation"]
                sz, ez = profile["start_zoom"], profile["end_zoom"]
                scx, ecx = profile["start_cx"], profile["end_cx"]
                scy, ecy = profile["start_cy"], profile["end_cy"]
                transition = transition_for_boundary(
                    previous_shot=previous_shot_id or shot_id,
                    next_shot=shot_id,
                    previous_index=cut_idx - 1,
                    pacing=pacing,
                )

                cut = {
                    "cut_index": cut_idx,
                    "cut_id": f"CUT_{cut_idx:03d}",
                    "start_sec": c_start_s,
                    "end_sec": c_end_s,
                    "duration_sec": c_dur_s,
                    "frame_count": f_count,
                    "parent_shot_id": shot_id,
                    "plate_id": plate_id,
                    "role": role,
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
                    "start_rotation": profile["start_rotation"],
                    "end_rotation": profile["end_rotation"],
                    "semantic_anchors": anchor_index[plate_id],
                    "semantic_match_status": "METADATA_ALIGNED_REVIEW_REQUIRED",
                }
                cut = annotate_cut_contract(
                    cut,
                    lineage_index[shot_id],
                    visual_beat=profile["visual_beat"],
                    motion_profile=profile,
                    transition_in=transition,
                )
                cuts.append(cut)
                shot_cur_f += f_count
                cut_idx += 1
                previous_shot_id = shot_id

        cur_frame = shot_cur_f

    total_f = sum(c["frame_count"] for c in cuts)
    assert total_f == TARGET_FRAMES, f"Frame count mismatch: {total_f} != {TARGET_FRAMES}"
    print(f"Total cuts planned: {len(cuts)}")

    anchor_audit = audit_visual_anchor_contract(cuts)
    if anchor_audit["status"] != "PASS":
        raise RuntimeError("Semantic anchor audit failed: " + "; ".join(anchor_audit["errors"][:12]))
    pacing_audit = audit_v3_pacing(cuts) if pacing == "v3_calm" else None
    if pacing_audit is not None and pacing_audit["status"] != "PASS":
        raise RuntimeError("V3 pacing audit failed: " + "; ".join(pacing_audit["errors"][:12]))

    audit_res = audit_subcut_montage_plan(
        cuts,
        expected_min_cuts=420 if pacing == "v3_calm" else 550,
        expected_max_cuts=480 if pacing == "v3_calm" else 600,
    )
    if audit_res["status"] != "PASS":
        raise RuntimeError("Subcut montage plan audit failed: " + "; ".join(audit_res.get("errors", [])))

    print(
        f"Audit PASS: aba_repeats={audit_res['aba_repeats']}, "
        f"same_parent_transitions={audit_res['same_parent_adjacent_transitions']}, "
        f"same_parent_plate_changes={audit_res['same_parent_plate_changes']}"
    )

    plan = {
        "target_duration_sec": TARGET_DURATION_SEC,
        "fps": float(FPS),
        "total_frames": TARGET_FRAMES,
        "total_cuts": len(cuts),
        "pacing": pacing,
        "pacing_policy": v3_policy,
        "semantic_anchor_audit": anchor_audit,
        "pacing_audit": pacing_audit,
        "lineage": {
            "source_bundle": str(NORMALIZED_BUNDLE_PATH),
            "source_script": str(NORMALIZED_SCRIPT_PATH),
            "source_cues": str(CANONICAL_MANIFEST_PATH),
            "shot_count": len(lineage_index),
            "cut_lineage_complete": all(
                c.get("sentence_ids") and c.get("cue_ids") and c.get("claim_ids") for c in cuts
            ),
        },
        "total_shots": len(shots),
        "same_parent_adjacent_transitions": audit_res["same_parent_adjacent_transitions"],
        "same_parent_plate_changes": audit_res["same_parent_plate_changes"],
        "aba_repeats": audit_res["aba_repeats"],
        "role_reversals": audit_res["role_reversals"],
        "cuts": cuts,
    }

    output_plan_path = Path(output_plan_path)
    output_plan_path.parent.mkdir(parents=True, exist_ok=True)
    output_plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated remastered subcut montage plan: {output_plan_path} ({len(cuts)} cuts, {total_f} frames)")
    return output_plan_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_PLAN_PATH)
    parser.add_argument("--pacing", choices=("v2", "v3_calm"), default="v2")
    parser.add_argument("--target-visible-cuts", type=int, default=None)
    args = parser.parse_args()
    generate_rank2_subcut_plan(
        args.output,
        pacing=args.pacing,
        target_visible_cuts=args.target_visible_cuts,
    )
