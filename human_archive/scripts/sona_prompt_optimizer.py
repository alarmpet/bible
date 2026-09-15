# -*- coding: utf-8 -*-
"""SONA Self-Optimizing Prompt Engine for Google Flow & Video Generation.
Inspired by Ruflo's SONA (Self-Optimizing Neural / Agentic Architecture).
Learns from approved image trajectories, enforces documentary photorealism,
prunes forbidden buzzwords, and optimizes 4-Look rotation cadence.
"""
from __future__ import annotations

import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FORBIDDEN_BUZZWORDS = [
    r"\bcinematic\b",
    r"\bphotorealistic\b",
    r"\b8k\b",
    r"\b4k\b",
    r"\bmasterpiece\b",
    r"\bultra[- ]detailed\b",
    r"\bhyperrealistic\b",
    r"\btrending on artstation\b",
    r"\bunreal engine\b",
    r"\bbeautiful\b",
    r"\bmaster\b",
]

BOTTOM_18_CLEAR_ZONE = "Keep bottom 18% of frame visually clear for subtitles added later."
SUBTITLE_EXCLUSIONS = "--no text, letters, numerals, watermarks, logos, titles, no subtitles, no text overlays, no burned-in captions, no watermark."

LOOK_PRESETS = {
    "LOOK_A": {"look_name": "Photoreal Aerial Drone", "lighting": "natural daylight, muted colors, 35mm lens"},
    "LOOK_B": {"look_name": "Matte Clay Render", "lighting": "soft studio light, untextured matte grey"},
    "LOOK_C": {"look_name": "Technical Cutaway", "lighting": "isometric perspective, matte materials"},
    "LOOK_D": {"look_name": "High-Contrast Schematic", "lighting": "pure black background, luminous white vector lines"},
    "LOOK_E": {"look_name": "Chiaroscuro Dark Cinematic", "lighting": "chiaroscuro dramatic lighting, deep shadows, golden rays"}
}


def purify_prompt(prompt: str) -> str:
    """Purify prompt by removing forbidden buzzwords, trademarks, and brand names."""
    clean = prompt
    for bw in FORBIDDEN_BUZZWORDS:
        clean = re.sub(bw, "", clean, flags=re.IGNORECASE)
    for brand in [r"\bNational Geographic\b", r"\bBBC\b", r"\bDiscovery\b"]:
        clean = re.sub(brand, "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


class SONAPromptOptimizer:
    """Self-optimizing prompt compiler that prunes buzzwords and optimizes documentary visual tokens."""

    def __init__(self, history_file: Optional[Path] = None):
        self.history_file = history_file or Path(r"D:\module\bible\human_archive\data\sona_prompt_history.json")
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.successful_tokens: Dict[str, int] = self._load_history()

    def _load_history(self) -> Dict[str, int]:
        if self.history_file.exists():
            try:
                return json.loads(self.history_file.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {
            "volumetric fog": 10,
            "natural daylight": 15,
            "35mm lens": 12,
            "archival texture": 8,
            "documentary cinematography": 20
        }

    def _save_history(self) -> None:
        try:
            self.history_file.write_text(json.dumps(self.successful_tokens, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def sanitize_prompt(self, raw_prompt: str) -> str:
        """Strip forbidden buzzwords and clean up duplicate whitespace."""
        clean = raw_prompt
        for bw in FORBIDDEN_BUZZWORDS:
            clean = re.sub(bw, "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def optimize_shot_prompt(
        self,
        narration: str,
        protagonist: str,
        shot_size: str,
        camera_motion: str = "push_in",
        look_style: str = "A"
    ) -> Dict[str, Any]:
        """Compile an optimized documentary visual prompt adhering to the 4-Look rotation."""
        scale_prefixes = {
            "extreme_wide": "Extreme wide panoramic aerial establishing vista, vast atmospheric landscape",
            "medium_action": "Cinematic medium eye-level action shot, dynamic documentary character framing",
            "macro_close_up": "Extreme macro close-up shot, shallow depth of field, razor-sharp texture focus",
            "top_down_insert": "Top-down bird's-eye archival insert shot, historic artifact focus, dramatic lighting"
        }
        prefix = scale_prefixes.get(shot_size, "Cinematic medium eye-level action shot")

        look_signatures = {
            "A": "photoreal aerial drone cinematography, natural daylight, muted colors, 35mm lens",
            "B": "untextured matte grey clay render, featureless white mannequin figures, soft studio light",
            "C": "clean technical cutaway, isometric perspective, matte materials, mechanical edge definition",
            "D": "pure black background, thin luminous white vector lines, high contrast schematic diagram",
            "E": "chiaroscuro dramatic lighting, deep shadows contrasted with sharp volumetric golden rays, epic atmospheric mist, ultra-realistic weathered stone textures, high visual tension, 35mm lens"
        }
        sig = look_signatures.get(look_style, look_signatures["A"])

        try:
            from lib.extract_key_visual_subject import extract_key_visual_subject
            extracted = extract_key_visual_subject(narration, protagonist=protagonist)
            visual_subject = extracted["compiled_subject"]
        except Exception:
            visual_subject = self.sanitize_prompt(narration)

        visual_prompt = (
            f"{prefix}. Subject: Authentic historical documentary for {protagonist}, {visual_subject}. "
            f"Style: {sig}. 25fps optical cadence, {camera_motion} camera movement. "
            f"{SUBTITLE_EXCLUSIONS} {BOTTOM_18_CLEAR_ZONE}"
        )

        final_prompt = self.sanitize_prompt(visual_prompt)

        return {
            "shot_size": shot_size,
            "camera_motion": camera_motion,
            "look_style": look_style,
            "optimized_prompt": final_prompt,
            "tokens_count": len(final_prompt.split()),
            "sanitized": True
        }

    def compile_dark_cinematic_prompt(
        self,
        subject_narration: str,
        protagonist: str,
        shot_size: str = "medium_action",
        camera_motion: str = "push_in"
    ) -> Dict[str, Any]:
        """Compile a Mystery-Wisdom hybrid dark cinematic prompt (Look E)."""
        return self.optimize_shot_prompt(
            narration=subject_narration,
            protagonist=protagonist,
            shot_size=shot_size,
            camera_motion=camera_motion,
            look_style="E"
        )

    def optimize_prompt(
        self,
        shot_id: str,
        narration: str,
        protagonist: str = "Civilization",
        shot_size: str = "medium_action",
        camera_motion: str = "push_in",
        look_key: str = "LOOK_E"
    ) -> str:
        """Convenience method returning the compiled string prompt directly."""
        style_letter = look_key.replace("LOOK_", "") if "LOOK_" in look_key else look_key
        res = self.optimize_shot_prompt(
            narration=narration,
            protagonist=protagonist,
            shot_size=shot_size,
            camera_motion=camera_motion,
            look_style=style_letter
        )
        return res["optimized_prompt"]

    def record_feedback(self, prompt: str, approved: bool = True) -> None:
        """Feedback loop: reward tokens of approved images, penalize rejected ones."""
        tokens = [t.strip().lower() for t in prompt.split(",") if len(t.strip()) > 3]
        for t in tokens:
            delta = 1 if approved else -1
            self.successful_tokens[t] = max(0, self.successful_tokens.get(t, 5) + delta)
        self._save_history()
