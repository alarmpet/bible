# -*- coding: utf-8 -*-
"""Produce a deterministic baseline report for script and visual quality."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _normalized_body(text: str) -> str:
    """Normalize punctuation/spacing for deterministic duplicate detection."""
    return re.sub(r"[^\w가-힣]+", "", _norm(text).lower())


def repetition_gate(sentences: list[dict[str, Any]], *, production: bool = False) -> dict[str, Any]:
    """Return a release decision for exact, normalized, and template repetition."""
    texts = [_norm(s.get("text") or s.get("display_text") or s.get("tts_text", "")) for s in sentences]
    exact = Counter(t for t in texts if t)
    normalized = Counter(_normalized_body(t) for t in texts if t)
    errors: list[dict[str, Any]] = []
    for value, count in exact.items():
        if count > 1:
            errors.append({"code": "DUPLICATE_TEXT", "text": value, "count": count})
    for value, count in normalized.items():
        if count > 1 and not any(e.get("code") == "DUPLICATE_TEXT" and _normalized_body(e["text"]) == value for e in errors):
            errors.append({"code": "NORMALIZED_DUPLICATE", "normalized": value, "count": count})
    # A short repeated template is a generator loop even when IDs differ.
    for n in range(3, min(8, len(texts)) + 1):
        grams = Counter(tuple(texts[i:i+n]) for i in range(len(texts)-n+1))
        for gram, count in grams.items():
            if count >= 3:
                errors.append({"code": "TEMPLATE_LOOP", "n": n, "count": count, "sentences": list(gram)})
                break
    return {"status": "FAIL" if errors else "PASS", "release_eligible": not errors and not production, "errors": errors}


def audit_episode(*, script_path: Path | None = None, manifest_path: Path | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {"schema_version": 1, "script": {}, "visual": {}}
    if script_path:
        data = json.loads(Path(script_path).read_text(encoding="utf-8"))
        texts = [_norm(s.get("text") or s.get("display_text") or s.get("tts_text", "")) for s in data.get("sentences", [])]
        counts = Counter(t for t in texts if t)
        report["script"] = {
            "sentence_count": len(texts),
            "unique_sentence_count": len(set(texts)),
            "duplicate_occurrences": sum(n - 1 for n in counts.values() if n > 1),
            "duplicate_texts": {t: n for t, n in counts.items() if n > 1},
        }
        report["script"]["repetition_gate"] = repetition_gate(data.get("sentences", []))
    if manifest_path:
        data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        assets = data.get("assets", [])
        prompts = [a.get("prompt_sha256") or a.get("prompt") or "" for a in assets]
        durations = []
        for asset in assets:
            value = asset.get("duration_sec", asset.get("duration_target_sec", 0))
            if isinstance(value, list):
                value = value[-1] if value else 0
            durations.append(float(value or 0))
        report["visual"] = {
            "asset_count": len(assets),
            "unique_prompt_count": len(set(prompts)),
            "prompt_reuse_count": len(prompts) - len(set(prompts)),
            "duration_over_25_sec": sum(d > 25 for d in durations),
            "max_duration_sec": max(durations, default=0),
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit_episode(script_path=args.script, manifest_path=args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
