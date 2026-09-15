from __future__ import annotations

from typing import Any


ALLOWED_LABELS = {"확인", "공식 발표", "논쟁 중", "미확인", "반박됨", "정정됨", "해석", "전망", "반응"}


def compile_overlay_events(rows: list[dict[str, Any]]) -> dict[str, Any]:
    events = []
    for row in rows:
        label = str(row.get("label", ""))
        if label not in ALLOWED_LABELS:
            raise ValueError(f"Unknown overlay label: {label}")
        text = str(row.get("text", ""))
        if len(text) > 28:
            raise ValueError("Overlay text exceeds two 14-character lines")
        events.append({"sentence_id": str(row["sentence_id"]), "label": label, "text": text})
    return {"schema_version": 1, "manifest_id": "overlay-nollam-v1", "base_image_text_policy": "no_glyph", "events": events}
