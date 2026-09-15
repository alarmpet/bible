from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import yaml


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _catalog(source_build: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    source_script = _load(source_build / "source" / "script_candidate.json")
    rows: dict[str, dict[str, Any]] = {str(row["sentence_id"]): row for row in source_script.get("sentences", [])}
    expansion_path = source_build / "source" / "script_expansion_v1.json"
    if expansion_path.exists():
        expansion = _load(expansion_path)
        for block in expansion.get("blocks", []):
            for row in block.get("sentences", []):
                rows.setdefault(str(row["sentence_id"]), row)
    audio = _load(source_build / "sentence_audio_manifest.json")
    return list(audio.get("sentences", [])), rows


def _asset_catalog(source_build: Path) -> dict[str, dict[str, Any]]:
    manifest = _load(source_build / "asset_manifest.json")
    requests = _load(source_build / "image_request_manifest.json")
    request_by_shot = {str(row.get("shot_id")): row for row in requests.get("requests", [])}
    approval_path = source_build / "approvals" / "visual_approval.json"
    approval_sha = sha256_file(approval_path) if approval_path.exists() else ""
    assets: dict[str, dict[str, Any]] = {}
    for asset in manifest.get("assets", []):
        shot_id = str(asset.get("shot_id"))
        req = request_by_shot.get(shot_id, {})
        provenance = asset.get("provenance") or {}
        request_sha = str(req.get("request_sha256") or provenance.get("request_contract_sha256") or "")
        if not request_sha:
            raise ValueError(f"asset {shot_id} has no request SHA")
        file_path = source_build / "images" / str(asset["file_path"])
        if not file_path.exists():
            raise FileNotFoundError(f"asset file missing: {file_path}")
        actual_sha = sha256_file(file_path)
        if actual_sha != str(asset.get("sha256", "")).upper():
            raise ValueError(f"asset SHA mismatch: {shot_id}")
        assets[shot_id] = {
            "source_asset_path": str(file_path),
            "source_asset_sha256": actual_sha,
            "source_request_sha256": request_sha,
            "approval_sha256": str(provenance.get("review_approval_sha256") or approval_sha),
            "card_id": asset.get("card_id"),
            "prompt_sha256": asset.get("prompt_sha256"),
            "source_shot_id": provenance.get("source_shot_id"),
        }
        if not assets[shot_id]["approval_sha256"]:
            raise ValueError(f"asset {shot_id} has no approval SHA")
    return assets


def compile_context_sample(
    source_build: Path,
    output_build: Path,
    count: int = 40,
    gap_sec: float = 0.30,
    append_sentence_ids: list[str] | None = None,
) -> Path:
    source_build = Path(source_build).resolve()
    output_build = Path(output_build).resolve()
    if count < 1:
        raise ValueError("count must be positive")
    audio_rows, source_rows = _catalog(source_build)
    asset_rows = _asset_catalog(source_build)
    append_sentence_ids = append_sentence_ids or []
    if len(append_sentence_ids) >= count:
        raise ValueError("append_sentence_ids must be shorter than count")
    by_id = {str(row["sentence_id"]): row for row in audio_rows}
    selected = audio_rows[: count - len(append_sentence_ids)]
    for sentence_id in append_sentence_ids:
        if sentence_id not in by_id:
            raise ValueError(f"appended sentence missing from source audio catalog: {sentence_id}")
        if any(str(row["sentence_id"]) == sentence_id for row in selected):
            raise ValueError(f"duplicate appended sentence: {sentence_id}")
        selected.append(by_id[sentence_id])
    if len(selected) < count:
        raise ValueError(f"source audio catalog has only {len(selected)} sentences")
    target_source = output_build / "source"
    approvals = target_source / "approvals"
    target_source.mkdir(parents=True, exist_ok=True)
    approvals.mkdir(parents=True, exist_ok=True)

    output_sentences: list[dict[str, Any]] = []
    segments: list[dict[str, Any]] = []
    for order, audio_row in enumerate(selected, start=1):
        sentence_id = str(audio_row["sentence_id"])
        source_row = source_rows.get(sentence_id)
        if source_row is None:
            # Some approved outro rows exist in the audio/fact catalog but not in
            # the compact candidate script. Carry the catalog text forward and
            # keep the sentence ID explicit so it can receive local review.
            source_row = {
                "sentence_id": sentence_id,
                "order": order,
                "chapter": int(audio_row.get("chapter", 1)),
                "beat": audio_row.get("beat", "body"),
                "display_text": str(audio_row.get("tts_text", "")),
                "tts_text": str(audio_row.get("tts_text", "")),
                "segments": [{"kind": audio_row.get("beat", "body"), "text": str(audio_row.get("tts_text", ""))}],
                "disclosure": None,
            }
        text = str(source_row.get("tts_text") or source_row.get("display_text") or audio_row.get("tts_text", ""))
        # The existing v6 audio catalog may be stale relative to the approved script.
        # Its duration is used only for selection; the new build must synthesize the
        # approved source text and records that it is a fresh TTS projection.
        source_segments = source_row.get("segments") or [{"kind": audio_row.get("beat", "body"), "text": text}]
        output_row = dict(source_row)
        output_row["order"] = order
        output_row["sentence_id"] = sentence_id
        output_row["tts_text"] = text
        output_row["display_text"] = text
        output_row["segments"] = source_segments
        output_sentences.append(output_row)

        asset = next(iter(asset_rows.values()))
        shot_id = f"ha002_v6_shot_{order:03d}"
        if shot_id in asset_rows:
            asset = asset_rows[shot_id]
        segments.append(
            {
                "sample_sentence_id": f"HA002-Q3-{order:03d}",
                "source_sentence_ids": [sentence_id],
                "edit_mode": "exact",
                "display_text": text,
                "tts_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest().upper(),
                "claim_ids": [s["claim_id"] for s in source_segments if s.get("claim_id")],
                "evidence_span_ids": [eid for s in source_segments for eid in s.get("evidence_span_ids", [])],
                "visual": {"asset_origin": "reuse", **asset},
                "source_audio_file": str(audio_row.get("audio_file", f"{sentence_id}.wav")),
                "source_audio_duration_sec": float(audio_row.get("duration_sec", 0.0)),
                "pause_after_sec": gap_sec if order < len(selected) else 0.0,
            }
        )

    script_output = {
        "schema_version": 1,
        "episode_id": "HA002",
        "persona": "ship_seonbi",
        "title": "장희빈, 사약 난동은 사실이었을까?",
        "target_duration_sec": 180,
        "sentences": output_sentences,
    }
    script_path = target_source / "script_candidate.json"
    script_path.write_text(json.dumps(script_output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    copy_names = [
        "claim_inventory_v2.json",
        "fact_check_report_v2.json",
        "persona_report_v2.json",
        "source_snapshot_manifest_v2.json",
    ]
    for name in copy_names:
        src = source_build / "source" / name
        if not src.exists():
            raise FileNotFoundError(src)
        shutil.copy2(src, target_source / name)
    approval_src = source_build / "source" / "approvals" / "fact_review_approval_v1.json"
    shutil.copy2(approval_src, approvals / approval_src.name)
    contract = {
        "schema_version": 1,
        "episode_id": "HA002",
        "build_id": output_build.name,
        "format_profile": "quick_3m",
        "publishable": True,
        "target_duration_sec": 180,
        "min_duration_sec": 170,
        "max_duration_sec": 190,
        "audio_mix_mode": "voice_only_exception_pending",
    }
    (target_source / "episode_contract.yaml").write_text(yaml.safe_dump(contract, allow_unicode=True, sort_keys=False), encoding="utf-8")

    artifact_paths = {
        "source_build_path": str(source_build),
        "source_script_path": str(script_path),
        "script_sha256": sha256_file(script_path),
    }
    for name, key in [
        ("claim_inventory_v2.json", "claims_sha256"),
        ("fact_check_report_v2.json", "fact_report_sha256"),
        ("approvals/fact_review_approval_v1.json", "fact_approval_sha256"),
        ("persona_report_v2.json", "persona_report_sha256"),
    ]:
        artifact_paths[key] = sha256_file(target_source / name)
    context_manifest = {
        "schema_version": 1,
        "episode_id": "HA002",
        "build_id": output_build.name,
        "delivery_profile": "quick_3m",
        "source_build_id": "full-v6-001",
        "source_artifacts": artifact_paths,
        "segments": segments,
    }
    manifest_path = target_source / "context_sample_manifest.json"
    manifest_path.write_text(json.dumps(context_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-build", type=Path, required=True)
    parser.add_argument("--output-build", type=Path, required=True)
    parser.add_argument("--count", type=int, default=40)
    parser.add_argument("--gap-sec", type=float, default=0.30)
    parser.add_argument("--append-sentence-id", action="append", default=[])
    args = parser.parse_args()
    path = compile_context_sample(
        args.source_build,
        args.output_build,
        count=args.count,
        gap_sec=args.gap_sec,
        append_sentence_ids=args.append_sentence_id,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
