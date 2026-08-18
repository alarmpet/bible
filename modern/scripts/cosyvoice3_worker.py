# -*- coding: utf-8 -*-
"""Runs inside the CosyVoice3 Python 3.10 venv. Do not import from SuperTonic.

Usage:
  .venv-cosy3/Scripts/python.exe cosyvoice3_worker.py --request-json request.json
  .venv-cosy3/Scripts/python.exe cosyvoice3_worker.py --request-json -
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path


def _configure_cpu(threads: int) -> None:
    threads = max(1, int(threads))
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    os.environ["OMP_NUM_THREADS"] = str(threads)
    os.environ["MKL_NUM_THREADS"] = str(threads)
    os.environ["OPENBLAS_NUM_THREADS"] = str(threads)
    os.environ["NUMEXPR_NUM_THREADS"] = str(threads)
    try:
        import torch

        torch.set_num_threads(threads)
        torch.set_num_interop_threads(max(1, min(2, threads)))
    except Exception:
        pass


def _split_clauses(text: str, max_chunk_length: int) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in re.split(r"(?<=[.!?다요까소라])\s+", text) if p.strip()]
    if not parts:
        parts = [text]
    out: list[str] = []
    buf = ""
    for part in parts:
        if buf and len(buf) + 1 + len(part) > max_chunk_length:
            out.append(buf)
            buf = part
        else:
            buf = f"{buf} {part}".strip() if buf else part
    if buf:
        out.append(buf)
    return out or [text]


def _load_model(cosy_root: Path, model_dir: Path):
    root = cosy_root.resolve()
    sys.path.insert(0, str(root))
    matcha = root / "third_party" / "Matcha-TTS"
    if matcha.exists():
        sys.path.insert(0, str(matcha))
    os.chdir(str(root))
    from cosyvoice.cli.cosyvoice import AutoModel  # type: ignore

    if not model_dir.exists():
        raise FileNotFoundError(f"Fun-CosyVoice3 model missing: {model_dir}")
    return AutoModel(model_dir=str(model_dir))


def _concat_wavs(chunks: list, sample_rate: int, silence_duration: float):
    import torch

    if not chunks:
        raise RuntimeError("CosyVoice3 produced no audio chunks")
    if len(chunks) == 1:
        return chunks[0]
    gap = int(max(0.0, float(silence_duration)) * sample_rate)
    sil = torch.zeros(1, gap) if gap else None
    pieces = []
    for i, wav in enumerate(chunks):
        pieces.append(wav)
        if sil is not None and i < len(chunks) - 1:
            pieces.append(sil)
    return torch.cat(pieces, dim=-1)


def _synthesize_one(model, item: dict) -> dict:
    import torchaudio

    text = (item.get("text") or "").strip()
    out = Path(item["output_path"])
    out.parent.mkdir(parents=True, exist_ok=True)
    ref = item.get("ref_wav")
    if not ref or not Path(ref).exists():
        raise FileNotFoundError(f"reference wav missing for CosyVoice3 clone: {ref}")
    mode = (item.get("mode") or "instruct2").lower()
    instruct = item.get("instruct") or "You are a helpful assistant.<|endofprompt|>"
    prompt_text = item.get("prompt_text") or ""
    max_chunk = int(item.get("max_chunk_length") or 90)
    silence = float(item.get("silence_duration") or 0.25)
    clauses = _split_clauses(text, max_chunk)
    started = time.perf_counter()
    wavs = []
    for clause in clauses:
        if mode == "zero_shot":
            gen = model.inference_zero_shot(
                clause,
                instruct + prompt_text,
                str(ref),
                stream=False,
            )
        else:
            gen = model.inference_instruct2(
                clause,
                instruct,
                str(ref),
                stream=False,
            )
        for piece in gen:
            wavs.append(piece["tts_speech"])
    audio = _concat_wavs(wavs, model.sample_rate, silence)
    torchaudio.save(str(out), audio, model.sample_rate)
    elapsed = time.perf_counter() - started
    duration = float(audio.shape[-1]) / float(model.sample_rate)
    rtf = (elapsed / duration) if duration > 0 else None
    return {
        "ok": True,
        "path": str(out),
        "duration": round(duration, 3),
        "sample_rate": int(model.sample_rate),
        "rtf": round(rtf, 3) if rtf is not None else None,
        "elapsed_seconds": round(elapsed, 3),
        "clauses": len(clauses),
        "voice": item.get("voice"),
        "mode": mode,
        "engine": "cosyvoice3",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--request-json", required=True, help="JSON file or - for stdin")
    args = ap.parse_args()
    raw = sys.stdin.read() if args.request_json == "-" else Path(args.request_json).read_text(encoding="utf-8")
    request = json.loads(raw)
    _configure_cpu(int(request.get("threads") or 3))
    cosy_root = Path(request.get("cosy_root") or r"D:\Fun-CosyVoice3")
    model_dir = Path(request.get("model_dir") or (cosy_root / "pretrained_models" / "Fun-CosyVoice3-0.5B"))
    try:
        model = _load_model(cosy_root, model_dir)
        if request.get("batch"):
            items = []
            for item in request["batch"]:
                merged = dict(request)
                merged.pop("batch", None)
                merged.update(item)
                items.append(_synthesize_one(model, merged))
            print(json.dumps({"ok": True, "items": items}, ensure_ascii=False))
            return 0
        print(json.dumps(_synthesize_one(model, request), ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
