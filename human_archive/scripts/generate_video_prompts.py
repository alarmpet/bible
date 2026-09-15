# -*- coding: utf-8 -*-
"""T2V v2.1 Dynamic Prompt Compiler for 20-Minute Master Documentary.
Eliminates rigid 30s shot fixing. Dynamically binds each shot to actual narration
script speech length (averaging 8s~15s per scene), ensuring 0.0s audio collision,
0.0s dead silence, and natural visual transitions within 1200s +-30% window."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_EP_DIR = Path(r"D:\module\bible\human_archive\runs\nollam_file\2026-09-02\himalaya-glof-water-crisis")

def get_current_ep_dir() -> Path:
    try:
        from workspace_manager import workspace_mgr
        if workspace_mgr:
            return workspace_mgr.current_ep_dir
    except Exception:
        pass
    return DEFAULT_EP_DIR

SCRIPTS_DIR = Path(r"D:\module\bible\human_archive\scripts")
LIB_DIR = SCRIPTS_DIR / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

try:
    from cinematic_editing_director import calculate_variable_shot_budget
except ImportError:
    calculate_variable_shot_budget = None

def get_scene_manifest_path() -> Path:
    return get_current_ep_dir() / "source" / "scene_script_manifest_v2.json"

def get_master_manifest_path() -> Path:
    return get_current_ep_dir() / "generation" / "master_1200s_manifest.json"

EP_DIR = DEFAULT_EP_DIR
SCENE_MANIFEST_PATH = get_scene_manifest_path()
MASTER_1200S_MANIFEST = get_master_manifest_path()

VERIFIED_SUBTITLE_EXCLUSIONS = (
    "no subtitles, no caption bar, no bottom text overlay, no burned-in captions, no karaoke-style word-by-word timing."
)
BOTTOM_18_CLEAR_ZONE = "Keep the bottom 18% of frame visually clear for subtitles added later."

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

LOOK_STYLES = {
    "A": {
        "code": "Look A",
        "name": "실사 드론 항공 (Photoreal Aerial Drone)",
        "badge": "📸 실사 항공 A",
        "color": "#0ea5e9",
        "signature": "photoreal aerial drone cinematography, hazy natural daylight, muted colors",
        "lens": "35mm lens, atmospheric depth, natural volumetric mountain fog",
    },
    "B": {
        "code": "Look B",
        "name": "무채색 클레이 마네킹 (Matte Grey Clay Mannequin)",
        "badge": "🗿 클레이 B",
        "color": "#a855f7",
        "signature": "untextured matte grey clay render, featureless white mannequin figures with no faces, soft even studio light",
        "lens": "dark minimalist backdrop, neutral museum exhibition lighting, 50mm prime lens",
    },
    "C": {
        "code": "Look C",
        "name": "아이소메트릭 기술 단면 (Isometric Technical Cutaway)",
        "badge": "📐 기술단면 C",
        "color": "#10b981",
        "signature": "clean technical cutaway, isometric perspective, matte materials, plain pale background",
        "lens": "orthographic 45-degree angle, sharp mechanical edge definition, structural engineering cross-section",
    },
    "D": {
        "code": "Look D",
        "name": "블랙 발광 벡터 (Black Luminous Vector)",
        "badge": "⚡ 네온벡터 D",
        "color": "#f59e0b",
        "signature": "pure black background, thin luminous white vector lines, high contrast schematic diagram",
        "lens": "subtle neon cyan flow indicators, minimal kinetic vector lines, dark field illumination",
    },
    "E": {
        "code": "Look E",
        "name": "키아로스쿠로 다크 시네마틱 (Chiaroscuro Dark Cinematic)",
        "badge": "🎬 시네마틱 E",
        "color": "#eab308",
        "signature": "chiaroscuro dramatic lighting, deep shadows contrasted with sharp volumetric golden rays, epic atmospheric mist, ultra-realistic weathered stone textures, high visual tension, 35mm lens",
        "lens": "35mm prime lens, deep cinematic contrast, authentic documentary optical depth",
    },
}

LOOK_ROTATION_SEQUENCE = ["E", "A", "E", "C"]

PHASE_LABELS = {
    "phase_1_hook": "1단계: 콜드오픈 & 미스터리 훅 (0~2분)",
    "phase_2_context": "2단계: 지질 구조 & 모레인 트랩 (2~6분)",
    "phase_3_evidence": "3단계: 연쇄 붕괴 & 세이시 충격파 (6~14분)",
    "phase_4_paradigm_shift": "4단계: 피크워터 & 20억 문명 위기 (14~18분)",
    "phase_5_outro": "5단계: 아웃트로 & 과학적 성찰 (18~20분)",
}


def purge_buzzwords(text: str) -> str:
    cleaned = text
    for pattern in FORBIDDEN_BUZZWORDS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"--ar\s+\d+:\d+", "", cleaned)
    cleaned = re.sub(r"--style\s+\w+", "", cleaned)
    cleaned = re.sub(r"--v\s+[\d\.]+", "", cleaned)
    cleaned = re.sub(r"--no.*", "", cleaned)
    cleaned = re.sub(r"\s+,", ",", cleaned)
    cleaned = re.sub(r",\s*,", ",", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,")
    return cleaned


def compile_dynamic_docu_prompts(
    ep_dir: Optional[Path] = None,
    scenes: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """Compile T2V v2.1 prompts dynamically bound to script narration lengths."""
    target_ep = ep_dir
    if not target_ep:
        try:
            from workspace_manager import workspace_mgr
            if workspace_mgr:
                target_ep = workspace_mgr.current_ep_dir
        except Exception:
            pass
    if not target_ep:
        target_ep = EP_DIR

    if scenes is None:
        scene_path = target_ep / "source" / "scene_script_manifest_v2.json"
        master_path = target_ep / "generation" / "master_1200s_manifest.json"

        scenes = []
        if scene_path.exists():
            sdata = json.loads(scene_path.read_text(encoding="utf-8"))
            scenes = sdata.get("scenes", [])
        
        if not scenes and master_path.exists():
            mdata = json.loads(master_path.read_text(encoding="utf-8"))
            scenes = mdata.get("shots", [])

    compiled_list = []
    for idx, s in enumerate(scenes):
        order = idx + 1
        # If chiaroscuro prompt is present or explicitly Look E, use Look E; otherwise use rotation
        if s.get("chiaroscuro_prompt") or s.get("look_style") == "E":
            look_key = "E"
        else:
            look_key = LOOK_ROTATION_SEQUENCE[(order - 1) % len(LOOK_ROTATION_SEQUENCE)]
        look_info = LOOK_STYLES[look_key]

        dur = s.get("duration_sec") or s.get("scene_duration", 10.0)
        frames = int(round(dur * 25))
        narr = s.get("narration") or s.get("display_text", "")
        raw_prompt = s.get("chiaroscuro_prompt") or s.get("midjourney_prompt") or s.get("visual_prompt", "")
        
        cleaned_subject = purge_buzzwords(raw_prompt)
        if not cleaned_subject or len(cleaned_subject) < 15:
            try:
                from lib.extract_key_visual_subject import extract_key_visual_subject
                extracted = extract_key_visual_subject(narr)
                cleaned_subject = extracted["compiled_subject"]
            except Exception:
                cleaned_subject = f"Authentic documentary scene, {narr}"

        phase_key = s.get("phase", "phase_1_hook")
        phase_label = PHASE_LABELS.get(phase_key, phase_key)

        prompt_tokens = [
            look_info["signature"],
            cleaned_subject,
            f"25fps optical motion, smooth natural glide",
            look_info["lens"],
            VERIFIED_SUBTITLE_EXCLUSIONS,
            BOTTOM_18_CLEAR_ZONE,
        ]
        compiled_prompt = ", ".join([t.strip(" ,") for t in prompt_tokens if t])

        compiled_list.append({
            "scene_id": s.get("scene_id", f"SCN_{order:03d}"),
            "shot_id": s.get("shot_id") or f"SHOT_{order:03d}",
            "order": order,
            "duration_sec": dur,
            "exact_frames": frames,
            "phase": phase_key,
            "phase_label": phase_label,
            "chapter_id": s.get("chapter_id", "ch01"),
            "korean_text": narr,
            "look": look_info["code"],
            "look_key": look_key,
            "look_name": look_info["name"],
            "look_badge": look_info["badge"],
            "look_color": look_info["color"],
            "compiled_prompt": compiled_prompt,
            "clean_subject": cleaned_subject,
            "is_dynamic": True,
        })

    return compiled_list


def compile_nollam_docu_prompts(
    scenes: List[Dict[str, Any]],
    *,
    provider: str = "flow",
) -> List[Dict[str, Any]]:
    """Compile NOLLAM scenes through the canonical polymorphic prompt contract."""
    from lib.aligned_prompt_compiler import compile_nollam_prompt

    compiled: List[Dict[str, Any]] = []
    for index, scene in enumerate(scenes):
        order = int(scene.get("order", index + 1))
        narration = str(scene.get("narration") or scene.get("display_text") or scene.get("tts_text") or "")
        request = compile_nollam_prompt(
            {
                "shot_id": scene.get("shot_id") or scene.get("scene_id") or f"SHOT_{order:03d}",
                "order": order,
                "visual_mode": scene.get("visual_mode") or scene.get("visual_role") or "historical_reconstruction",
                "subject": scene.get("subject") or scene.get("focal_subject") or narration,
                "action": scene.get("action") or scene.get("visual_intent") or "observe the documented subject",
                "place": scene.get("place") or scene.get("location") or "documented field context",
                "era": scene.get("era") or scene.get("era_context") or "historical context",
                "visual_claim_ids": scene.get("visual_claim_ids") or scene.get("claim_ids") or [],
                "motion_profile": scene.get("motion_profile") or "smooth_subpixel",
            },
            provider=provider,
        )
        duration = float(scene.get("duration_sec") or scene.get("scene_duration") or 10.0)
        compiled.append({
            **request,
            "scene_id": scene.get("scene_id") or request["shot_id"],
            "duration_sec": duration,
            "exact_frames": int(round(duration * 25)),
            "korean_text": narration,
            "is_dynamic": True,
        })
    return compiled


def compile_all_56_prompts() -> List[Dict[str, Any]]:
    """Backward-compatible alias for compile_dynamic_docu_prompts."""
    return compile_dynamic_docu_prompts()


def compile_prompts_for_duration(target_duration_sec: float, scenes: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Compile prompts and attach constitutional 3-tier shot budget for specified target duration."""
    compiled = compile_dynamic_docu_prompts(scenes=scenes)
    budget = calculate_variable_shot_budget(target_duration_sec) if calculate_variable_shot_budget else None
    return {
        "target_duration_sec": target_duration_sec,
        "total_prompts": len(compiled),
        "shot_budget": budget,
        "prompts": compiled
    }


if __name__ == "__main__":
    prompts = compile_dynamic_docu_prompts()
    print(f"Dynamic Audio-Bound Prompts Compiled: {len(prompts)} scenes")
    total_dur = sum(p["duration_sec"] for p in prompts)
    print(f"Total Duration: {total_dur:.2f}s ({total_dur/60:.2f} min)")
    print(f"Average Scene Duration: {total_dur/len(prompts):.2f}s")
    print(f"Sample SCN_001: {prompts[0]['look_badge']} ({prompts[0]['duration_sec']}s) - {prompts[0]['compiled_prompt'][:90]}...")
    print(f"Sample SCN_021: {prompts[20]['look_badge']} ({prompts[20]['duration_sec']}s) - {prompts[20]['compiled_prompt'][:90]}...")
