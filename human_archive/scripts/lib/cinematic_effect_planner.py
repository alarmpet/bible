# -*- coding: utf-8 -*-
"""Deterministic, beat-aware cinematic effect planner (SSOT).

Enforces:
1. 3-Cut Visible FLOW opening trilogy (order=1 / opening_group).
2. 7-beat deterministic motion grammar (question, reveal, threat, contradiction, evidence, consequence, pause).
3. Anti-monotony diversity window (no consecutive identical family/axis > 2, 10-shot window family >= 4).
4. Long-take (>=30s) Tri-Phasic motion (Ambient Drift 35% -> Dynamic Approach 35% -> Focal Lock 30%).
5. Subtitle safe area protection (Y-axis focal anchor clamped to <= 0.75).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Protocol, Tuple


@dataclass(frozen=True)
class MotionPhase:
    duration_ratio: float
    zoom_start: float
    zoom_end: float
    center_start: Tuple[float, float]  # (x, y) normalized [0.0, 1.0]
    center_end: Tuple[float, float]
    easing: str = "cosine_s_curve"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "duration_ratio": self.duration_ratio,
            "zoom_start": self.zoom_start,
            "zoom_end": self.zoom_end,
            "center_start": list(self.center_start),
            "center_end": list(self.center_end),
            "easing": self.easing,
        }


@dataclass(frozen=True)
class PlannedProfile:
    effect_id: str
    motion_family: str  # "reframe", "lateral_reveal", "threat_push", "counter_axis_pan", "evidence_macro", "slow_pull_out", "ambient_drift", "perceptual_cut"
    axis: str           # "zoom_in", "zoom_out", "pan_left", "pan_right", "tilt_up", "tilt_down", "drift", "diagonal"
    focal_anchor: Tuple[float, float]
    phases: Tuple[MotionPhase, ...]
    transition_out: str # "hard_cut", "match_cut", "dissolve"
    reason_codes: Tuple[str, ...]
    pacing_tier: str = "tier_2_context"
    editing_tempo: str = "context_mid"
    sub_type: str = "subpixel_ken_burns"
    clamped_for_subtitles: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return {
            "effect_id": self.effect_id,
            "motion_family": self.motion_family,
            "axis": self.axis,
            "focal_anchor": list(self.focal_anchor),
            "phases": [p.as_dict() for p in self.phases],
            "transition_out": self.transition_out,
            "reason_codes": list(self.reason_codes),
            "pacing_tier": self.pacing_tier,
            "editing_tempo": self.editing_tempo,
            "sub_type": self.sub_type,
            "clamped_for_subtitles": self.clamped_for_subtitles,
        }


class CinematicEffectPlannerProtocol(Protocol):
    def plan_shot_effect(
        self,
        scene: Dict[str, Any],
        recent_history: List[PlannedProfile],
        next_scene: Optional[Dict[str, Any]] = None,
    ) -> PlannedProfile: ...

    def plan_opening_group(
        self,
        master_shot: Dict[str, Any],
    ) -> List[PlannedProfile]: ...


class CinematicEffectPlanner:
    """Deterministic scoring planner enforcing anti-monotony and beat alignment."""

    BEAT_FAMILY_MAPPING = {
        "question": ("reframe", "zoom_in"),
        "reveal": ("lateral_reveal", "pan_right"),
        "threat": ("threat_push", "zoom_in"),
        "contradiction": ("counter_axis_pan", "pan_left"),
        "evidence": ("evidence_macro", "zoom_in"),
        "consequence": ("slow_pull_out", "zoom_out"),
        "pause": ("ambient_drift", "drift"),
    }

    ALTERNATIVE_FAMILIES = [
        ("reframe", "zoom_in"),
        ("lateral_reveal", "pan_right"),
        ("slow_pull_out", "zoom_out"),
        ("lateral_reveal", "pan_left"),
        ("threat_push", "zoom_in"),
        ("ambient_drift", "drift"),
        ("counter_axis_pan", "tilt_up"),
        ("evidence_macro", "zoom_in"),
    ]

    def plan_opening_group(self, master_shot: Dict[str, Any]) -> List[PlannedProfile]:
        """Strictly generates the 3-cut visible opening profile for scene 1."""
        total_dur = float(master_shot.get("scene_duration", 11.0))
        # Default ratios: 3.0s, 3.5s, 4.5s normalized to total_dur
        r1 = round(3.0 / 11.0, 4)
        r2 = round(3.5 / 11.0, 4)
        r3 = round(1.0 - r1 - r2, 4)

        c1 = PlannedProfile(
            effect_id="opening_context_wide_drift",
            motion_family="ambient_drift",
            axis="pan_right",
            focal_anchor=(0.5, 0.45),
            phases=(
                MotionPhase(
                    duration_ratio=1.0,
                    zoom_start=1.0,
                    zoom_end=1.04,
                    center_start=(0.48, 0.45),
                    center_end=(0.52, 0.45),
                ),
            ),
            transition_out="dissolve",
            reason_codes=("opening_pacing", "wide_context_anchor"),
            pacing_tier="tier_1_hook",
            editing_tempo="rapid_montage",
            sub_type="opening_cut_context_wide",
        )

        c2 = PlannedProfile(
            effect_id="opening_subject_action_push",
            motion_family="reframe",
            axis="zoom_in",
            focal_anchor=(0.5, 0.5),
            phases=(
                MotionPhase(
                    duration_ratio=1.0,
                    zoom_start=1.04,
                    zoom_end=1.12,
                    center_start=(0.5, 0.5),
                    center_end=(0.5, 0.5),
                ),
            ),
            transition_out="dissolve",
            reason_codes=("opening_pacing", "subject_engagement"),
            pacing_tier="tier_1_hook",
            editing_tempo="rapid_montage",
            sub_type="opening_cut_subject_action",
        )

        c3 = PlannedProfile(
            effect_id="opening_evidence_detail_macro",
            motion_family="evidence_macro",
            axis="zoom_in",
            focal_anchor=(0.55, 0.55),
            phases=(
                MotionPhase(
                    duration_ratio=1.0,
                    zoom_start=1.10,
                    zoom_end=1.18,
                    center_start=(0.52, 0.52),
                    center_end=(0.55, 0.55),
                ),
            ),
            transition_out="hard_cut",
            reason_codes=("opening_pacing", "evidence_lock"),
            pacing_tier="tier_1_hook",
            editing_tempo="rapid_montage",
            sub_type="opening_cut_evidence_detail",
        )

        return [c1, c2, c3]

    def infer_beat_type(self, scene: Dict[str, Any]) -> str:
        """Infer narrative beat from explicit beat_type or semantic text."""
        if scene.get("beat_type"):
            b = str(scene["beat_type"]).lower().strip()
            if b in self.BEAT_FAMILY_MAPPING:
                return b

        text = (scene.get("narration") or scene.get("display_text") or scene.get("tts_text") or "").strip()
        t_lower = text.lower()

        if any(w in t_lower for w in ["왜", "?", "수수께끼", "의문", "비밀", "누가", "어디로", "어떻게"]):
            return "question"
        if any(w in t_lower for w in ["사료", "기록", "유골", "화석", "발굴", "증거", "데이터", "분석", "석순", "라이다", "동위원소", "게놈", "도장", "문서"]):
            return "evidence"
        if any(w in t_lower for w in ["멸종", "위기", "한랭화", "사피엔스", "충돌", "전쟁", "살육", "빙하기", "고갈", "폭동", "추위", "절체절명"]):
            return "threat"
        if any(w in t_lower for w in ["그러나", "하지만", "반면", "역설", "상식과 달리", "실제로는", "뜻밖에도", "그런데"]):
            return "contradiction"
        if any(w in t_lower for w in ["사라졌다", "최후", "몰락", "결국", "결과", "멸망", "역사의 뒤안길", "소멸", "끝내"]):
            return "consequence"
        if any(w in t_lower for w in ["침묵", "기억", "바라본다", "지금도", "남겨진", "성찰", "시간이 흘러", "여운"]):
            return "pause"
        return "reveal"

    def plan_shot_effect(
        self,
        scene: Dict[str, Any],
        recent_history: List[PlannedProfile],
        next_scene: Optional[Dict[str, Any]] = None,
    ) -> PlannedProfile:
        order = scene.get("order")
        if order is None:
            shot_id = str(scene.get("shot_id", ""))
            import re
            m = re.search(r"\d+", shot_id)
            order = int(m.group(0)) if m else 2
        else:
            order = int(order)

        scene_role = str(scene.get("scene_role", ""))

        if order == 1 or scene_role == "opening_group":
            raise ValueError("Use plan_opening_group for order=1 / opening_group scenes")

        beat = self.infer_beat_type(scene)
        dur = float(scene.get("scene_duration", scene.get("duration_sec", 10.0)))
        shot_id = scene.get("shot_id", f"SHOT_{order:03d}")

        # Primary candidate from beat mapping
        preferred_family, preferred_axis = self.BEAT_FAMILY_MAPPING.get(beat, ("reveal", "pan_right"))

        # Check anti-monotony invariants against recent history
        family = preferred_family
        axis = preferred_axis

        # Rule 1: No identical motion_family > 2 in a row
        if len(recent_history) >= 2:
            f_streak = (recent_history[-1].motion_family == family and recent_history[-2].motion_family == family)
            a_streak = (recent_history[-1].axis == axis and recent_history[-2].axis == axis)
            if f_streak or a_streak:
                # Find best alternative from list that does not violate anti-monotony
                for alt_f, alt_a in self.ALTERNATIVE_FAMILIES:
                    alt_f_streak = (recent_history[-1].motion_family == alt_f and recent_history[-2].motion_family == alt_f)
                    alt_a_streak = (recent_history[-1].axis == alt_a and recent_history[-2].axis == alt_a)
                    if not alt_f_streak and not alt_a_streak:
                        family = alt_f
                        axis = alt_a
                        break

        # Focal anchor & Subtitle Safe Area clamping (Y <= 0.75)
        raw_anchor = scene.get("focal_anchor", (0.5, 0.5))
        ax = float(raw_anchor[0])
        ay = float(raw_anchor[1])
        clamped = False
        if ay > 0.75:
            ay = 0.75
            clamped = True
        focal_anchor = (round(ax, 3), round(ay, 3))

        # Build trajectory phases
        reason_codes = [f"beat_{beat}"]
        if clamped:
            reason_codes.append("clamped_for_subtitles")

        # Long-take (>= 30.0s): Force Tri-Phasic Internal Motion
        if dur >= 30.0:
            tier = "tier_3_deep"
            tempo = "deep_contemplative"
            sub_type = "tri_phasic_ken_burns"
            reason_codes.append("long_take_tri_phasic")

            p1 = MotionPhase(
                duration_ratio=0.35,
                zoom_start=1.02,
                zoom_end=1.02,
                center_start=(max(0.40, ax - 0.04), ay),
                center_end=(min(0.60, ax + 0.04), ay),
                easing="linear",
            )
            p2 = MotionPhase(
                duration_ratio=0.35,
                zoom_start=1.02,
                zoom_end=1.18,
                center_start=(min(0.60, ax + 0.04), ay),
                center_end=(ax, ay),
                easing="cosine_s_curve",
            )
            p3 = MotionPhase(
                duration_ratio=0.30,
                zoom_start=1.18,
                zoom_end=1.19,
                center_start=(ax, ay),
                center_end=(ax, ay),
                easing="cosine_s_curve",
            )
            phases = (p1, p2, p3)
        elif dur >= 15.0:
            tier = "tier_2_context"
            tempo = "context_mid"
            sub_type = "subpixel_ken_burns"
            # Two-phase biphasic motion
            p1 = MotionPhase(
                duration_ratio=0.50,
                zoom_start=1.00,
                zoom_end=1.08,
                center_start=(ax - 0.02, ay),
                center_end=(ax, ay),
                easing="cosine_s_curve",
            )
            p2 = MotionPhase(
                duration_ratio=0.50,
                zoom_start=1.08,
                zoom_end=1.15,
                center_start=(ax, ay),
                center_end=(ax + 0.02, ay),
                easing="cosine_s_curve",
            )
            phases = (p1, p2)
        else:
            tier = "tier_1_hook" if order <= 11 else "tier_2_context"
            tempo = "rapid_montage" if tier == "tier_1_hook" else "context_mid"
            sub_type = "subpixel_ken_burns"
            # Single phase dynamic motion
            z_start = 1.00 if axis != "zoom_out" else 1.15
            z_end = 1.15 if axis != "zoom_out" else 1.00
            c_start = (ax - 0.03, ay) if "left" in axis else ((ax + 0.03, ay) if "right" in axis else (ax, ay))
            c_end = (ax + 0.03, ay) if "left" in axis else ((ax - 0.03, ay) if "right" in axis else (ax, ay))
            phases = (
                MotionPhase(
                    duration_ratio=1.0,
                    zoom_start=z_start,
                    zoom_end=z_end,
                    center_start=c_start,
                    center_end=c_end,
                    easing="cosine_s_curve",
                ),
            )

        effect_id = f"{shot_id.lower()}_{family}_{axis}"

        return PlannedProfile(
            effect_id=effect_id,
            motion_family=family,
            axis=axis,
            focal_anchor=focal_anchor,
            phases=phases,
            transition_out="hard_cut",
            reason_codes=tuple(reason_codes),
            pacing_tier=tier,
            editing_tempo=tempo,
            sub_type=sub_type,
            clamped_for_subtitles=clamped,
        )

    def evaluate_diversity_window(self, profiles: List[PlannedProfile], window_size: int = 10) -> Dict[str, Any]:
        """Verify diversity invariants across profile sequence:
        1. No consecutive identical family > 2.
        2. No consecutive identical axis > 2.
        3. Sliding window of size 10 has at least 4 unique families.
        """
        violations = []
        max_f_streak = 1
        max_a_streak = 1
        cur_f_streak = 1
        cur_a_streak = 1

        for i in range(1, len(profiles)):
            if profiles[i].motion_family == profiles[i - 1].motion_family:
                cur_f_streak += 1
                max_f_streak = max(max_f_streak, cur_f_streak)
                if cur_f_streak > 2:
                    violations.append(f"Family streak {cur_f_streak} at index {i} ({profiles[i].motion_family})")
            else:
                cur_f_streak = 1

            if profiles[i].axis == profiles[i - 1].axis:
                cur_a_streak += 1
                max_a_streak = max(max_a_streak, cur_a_streak)
                if cur_a_streak > 2:
                    violations.append(f"Axis streak {cur_a_streak} at index {i} ({profiles[i].axis})")
            else:
                cur_a_streak = 1

        min_window_families = 999
        if len(profiles) >= window_size:
            for w in range(len(profiles) - window_size + 1):
                window = profiles[w:w + window_size]
                unique_f = len(set(p.motion_family for p in window))
                min_window_families = min(min_window_families, unique_f)
                if unique_f < 4:
                    violations.append(f"Window [{w}:{w+window_size}] has only {unique_f} unique families (min 4 required)")
        else:
            min_window_families = len(set(p.motion_family for p in profiles))

        return {
            "valid": len(violations) == 0,
            "max_consecutive_family": max_f_streak,
            "max_consecutive_axis": max_a_streak,
            "min_window_family_count": min_window_families,
            "violations": violations,
        }
