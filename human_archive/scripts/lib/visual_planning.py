from __future__ import annotations

import hashlib
from typing import Any


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def build_visual_contract(script: dict[str, Any], scene_specs: list[dict[str, Any]]) -> dict[str, Any]:
    sentences = {s["sentence_id"]: (s.get("display_text") or s.get("tts_text") or s.get("text", "")) for s in script.get("sentences", [])}
    captions = []
    scenes = []
    covered: set[str] = set()
    for order, spec in enumerate(scene_specs, start=1):
        scene_id = spec["scene_id"]
        ids = spec.get("sentence_ids", [])
        for sid in ids:
            text = sentences[sid]
            captions.append({"caption_id": f"cap-{sid}", "sentence_id": sid, "text_span": text, "text_sha256": _sha(text), "scene_id": scene_id})
            covered.add(sid)
        scenes.append({
            "scene_id": scene_id, "order": order, "visual_beat": spec["visual_beat"],
            "subject_refs": spec.get("subject_refs", []), "subject_lock": bool(spec.get("subject_refs")),
            "place": spec["place"], "era": spec["era"], "action": spec["action"],
            "depiction_mode": spec.get("depiction_mode", "documented"), "tone": spec.get("tone", "neutral"),
            "must_not": spec.get("must_not", []), "disclosure": spec.get("disclosure", "")
        })
    if covered != set(sentences):
        missing = sorted(set(sentences) - covered)
        raise ValueError(f"Scene plan does not cover approved sentences: {missing}")
    return {"schema_version": 1, "episode_id": script.get("episode_id", ""), "captions": captions, "scenes": scenes}
