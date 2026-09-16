from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import struct
import wave
from pathlib import Path
from typing import Any

from lib.audio_timeline import get_wav_duration
from lib.sentence_audio_timeline import build_sentence_rows, validate_sentence_timeline
from lib.tts_provider import SupertonicHttpProvider, ToneFixtureProvider


SAMPLE_RATE = 48_000
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


_DEFAULT_VOICE = "M4"


def _resolve_voice(
    voice: str | None,
    voice_lock_id: str | None,
    script: dict[str, Any],
) -> str:
    """Resolve the SuperTonic3 voice code to synthesize with.

    Found live running a real nollam_file_v1 episode (2026-09-16): this
    function's only caller previously hardcoded voice="M4" whenever no
    explicit --voice was given, and the CLI never exposed a --voice/
    --voice-lock-id flag at all -- so CLAUDE.md's own documented Step 2
    command (`build_sentence_audio_master.py --script ... --audio-mode
    supertonic3 ...`, no voice flag) silently synthesized every nollam_file_v1
    episode with M4 instead of the mandated M2_WARM
    (voice=M2, per channel_profiles.yaml and CLAUDE.md section 4). Per-episode
    one-off scripts (run_neanderthal_full_pipeline.py, run_san_jose_full_
    pipeline.py) worked around this by calling the Python function directly
    with an explicit voice="M2" -- but the general, documented CLI path had
    no way to do that and no test ever caught it.

    Priority: explicit --voice > explicit --voice-lock-id > the script's own
    top-level voice_lock_id field (script_candidate.json already declares
    this) > the historical M4 default, kept only for callers that declare no
    lock at all.
    """
    if voice:
        return voice
    resolved_lock_id = voice_lock_id or script.get("voice_lock_id")
    if resolved_lock_id:
        return str(resolved_lock_id).split("_")[0]
    return _DEFAULT_VOICE


def _assemble_pcm_master(
    rows: list[dict[str, Any]],
    sentence_dir: Path,
    master_path: Path,
    *,
    gap_sec: float,
) -> None:
    """Concatenate normalized phrase WAVs and materialize deterministic room tone."""
    gap_frames = round(SAMPLE_RATE * gap_sec)
    room_tone = bytearray(gap_frames * CHANNELS * SAMPLE_WIDTH_BYTES)
    # Keep the bed well below the -35 dB active-speech threshold while making
    # the inter-sentence bridge a real finite signal rather than zero padding.
    amplitude = int(32767 * (10 ** (-48.0 / 20.0)))
    for frame in range(gap_frames):
        sample = int(amplitude * (
            0.65 * math.sin(2.0 * math.pi * 97.0 * frame / SAMPLE_RATE)
            + 0.35 * math.sin(2.0 * math.pi * 131.0 * frame / SAMPLE_RATE)
        ))
        struct.pack_into("<h", room_tone, frame * SAMPLE_WIDTH_BYTES, sample)
    master_path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(master_path), "wb") as writer:
        writer.setnchannels(CHANNELS)
        writer.setsampwidth(SAMPLE_WIDTH_BYTES)
        writer.setframerate(SAMPLE_RATE)

        for index, row in enumerate(rows):
            phrase_path = sentence_dir / str(row["audio_file"])
            with wave.open(str(phrase_path), "rb") as reader:
                params = (
                    reader.getnchannels(),
                    reader.getsampwidth(),
                    reader.getframerate(),
                    reader.getcomptype(),
                )
                expected = (CHANNELS, SAMPLE_WIDTH_BYTES, SAMPLE_RATE, "NONE")
                if params != expected:
                    raise ValueError(
                        f"sentence WAV must be 48kHz mono PCM16: {phrase_path} has {params}"
                    )
                writer.writeframes(reader.readframes(reader.getnframes()))
            if index + 1 < len(rows) and gap_frames:
                writer.writeframes(room_tone)


def _load_reusable_provenance(
    script_path: Path,
    build_dir: Path,
    ordered_sentences: list[dict[str, Any]],
    *,
    expected_provider: str,
) -> dict[str, dict[str, Any]]:
    manifest_path = build_dir / "sentence_audio_manifest.json"
    if not manifest_path.exists():
        raise ValueError("--reuse-existing requires sentence_audio_manifest.json")
    existing = json.loads(manifest_path.read_text(encoding="utf-8"))
    script_sha = hashlib.sha256(script_path.read_bytes()).hexdigest()
    if str(existing.get("script_sha256", "")).lower() != script_sha.lower():
        raise ValueError("existing sentence audio belongs to a different script hash")

    rows = {str(row.get("sentence_id", "")): row for row in existing.get("sentences", [])}
    provenance: dict[str, dict[str, Any]] = {}
    for sentence in ordered_sentences:
        sentence_id = str(sentence["sentence_id"])
        row = rows.get(sentence_id)
        if not row:
            raise ValueError(f"existing sentence audio row is missing: {sentence_id}")
        info = dict(row.get("provenance") or {})
        if str(info.get("provider", "")) != expected_provider:
            raise ValueError(
                f"existing provider mismatch for {sentence_id}: "
                f"expected {expected_provider}, got {info.get('provider')}"
            )
        if str(info.get("text_sha256", "")).upper() != _text_sha256(str(sentence["tts_text"])):
            raise ValueError(f"existing sentence text hash is stale: {sentence_id}")
        phrase_path = build_dir / "audio" / "sentences" / f"{sentence_id}.wav"
        if not phrase_path.exists():
            raise ValueError(f"existing sentence WAV is missing: {sentence_id}")
        provenance[sentence_id] = info
    return provenance


def _load_cross_build_reuse_pool(
    source_builds: list[Path],
    *,
    expected_provider: str,
) -> dict[tuple[str, str], dict[str, Any]]:
    pool: dict[tuple[str, str], dict[str, Any]] = {}
    for source_build in source_builds:
        source_build = Path(source_build)
        manifest_path = source_build / "sentence_audio_manifest.json"
        if not manifest_path.exists():
            raise ValueError(
                f"reuse source is missing sentence_audio_manifest.json: {source_build}"
            )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for row in manifest.get("sentences", []):
            provenance = dict(row.get("provenance") or {})
            provider = str(provenance.get("provider", ""))
            if provider != expected_provider:
                continue
            text = str(row.get("tts_text", ""))
            text_sha = str(provenance.get("text_sha256", "")).upper()
            if not text or text_sha != _text_sha256(text):
                raise ValueError(
                    f"reuse source has stale text provenance: "
                    f"{source_build} / {row.get('sentence_id')}"
                )
            audio_file = str(
                row.get("audio_file") or f"{row.get('sentence_id', '')}.wav"
            )
            phrase_path = source_build / "audio" / "sentences" / audio_file
            if not phrase_path.exists():
                raise ValueError(f"reuse source WAV is missing: {phrase_path}")
            pool.setdefault(
                (provider, text_sha),
                {
                    "build_dir": source_build,
                    "sentence_id": str(row.get("sentence_id", "")),
                    "phrase_path": phrase_path,
                    "provenance": provenance,
                },
            )
    return pool


def build_sentence_audio_master(
    script_path: Path,
    build_dir: Path,
    audio_mode: str = "supertonic3",
    tts_url: str | None = None,
    gap_sec: float = 0.35,
    *,
    reuse_existing: bool = False,
    reuse_from_builds: list[Path] | None = None,
    voice_lock_id: str | None = None,
    voice: str | None = None,
    speed: float | None = None,
    total_step: int | None = None,
) -> Path:
    script_path = Path(script_path)
    build_dir = Path(build_dir)
    script = json.loads(script_path.read_text(encoding="utf-8"))
    ordered_sentences = sorted(script["sentences"], key=lambda row: int(row["order"]))
    sentence_dir = build_dir / "audio" / "sentences"
    sentence_dir.mkdir(parents=True, exist_ok=True)

    if audio_mode == "fixture":
        provider = ToneFixtureProvider()
        expected_provider = "tone_fixture"
    elif audio_mode == "supertonic3":
        provider = SupertonicHttpProvider(tts_url) if tts_url else SupertonicHttpProvider()
        expected_provider = "supertonic3_http"
    else:
        raise ValueError(f"unsupported audio mode: {audio_mode}")

    if reuse_existing and reuse_from_builds:
        raise ValueError("--reuse-existing cannot be combined with --reuse-from-build")

    reused_phrase_count = 0
    synthesized_phrase_count = 0
    if reuse_existing:
        provenance = _load_reusable_provenance(
            script_path,
            build_dir,
            ordered_sentences,
            expected_provider=expected_provider,
        )
        reused_phrase_count = len(ordered_sentences)
    else:
        provenance = {}
        reuse_pool = _load_cross_build_reuse_pool(
            [Path(path) for path in (reuse_from_builds or [])],
            expected_provider=expected_provider,
        )
        for sentence in ordered_sentences:
            sentence_id = str(sentence["sentence_id"])
            phrase_path = sentence_dir / f"{sentence_id}.wav"
            text = str(sentence["tts_text"])
            text_sha = _text_sha256(text)
            reusable = reuse_pool.get((expected_provider, text_sha))
            if reusable:
                source_phrase = Path(reusable["phrase_path"])
                if source_phrase.resolve() != phrase_path.resolve():
                    shutil.copy2(source_phrase, phrase_path)
                info = dict(reusable["provenance"])
                info.update(
                    {
                        "reuse_mode": "provider_text_sha256",
                        "reused_from_build": str(reusable["build_dir"]),
                        "reused_from_sentence_id": reusable["sentence_id"],
                    }
                )
                provenance[sentence_id] = info
                reused_phrase_count += 1
            else:
                if audio_mode == "supertonic3":
                    provenance[sentence_id] = provider.synthesize_phrase(
                        text,
                        phrase_path,
                        speed=float(speed if speed is not None else 0.94),
                        voice=_resolve_voice(voice, voice_lock_id, script),
                        total_step=int(total_step if total_step is not None else 10),
                        silence_duration=0.0,
                    )
                else:
                    provenance[sentence_id] = provider.synthesize_phrase(text, phrase_path, silence_duration=0.0)
                synthesized_phrase_count += 1

    durations = {
        str(sentence["sentence_id"]): get_wav_duration(
            sentence_dir / f"{sentence['sentence_id']}.wav"
        )
        for sentence in ordered_sentences
    }
    wav_sha256_by_id = {
        str(sentence["sentence_id"]): hashlib.sha256(
            (sentence_dir / f"{sentence['sentence_id']}.wav").read_bytes()
        ).hexdigest()
        for sentence in ordered_sentences
    }
    rows = build_sentence_rows(ordered_sentences, durations, gap_sec, wav_sha256_by_id)
    for row in rows:
        row["provenance"] = provenance[str(row["sentence_id"])]

    master = build_dir / "master_audio_48k.wav"
    _assemble_pcm_master(rows, sentence_dir, master, gap_sec=gap_sec)
    manifest = {
        "schema_version": 1,
        "episode_id": script.get("episode_id", ""),
        "script_sha256": hashlib.sha256(script_path.read_bytes()).hexdigest(),
        "master_audio": str(master),
        "total_duration_sec": round(get_wav_duration(master), 3),
        "gap_sec": gap_sec,
        "room_tone": {
            "mode": "deterministic_low_level",
            "peak_dbfs": -48.0,
            "sample_rate": SAMPLE_RATE,
            "channels": CHANNELS,
            "duration_sec": gap_sec,
        },
        "reuse_summary": {
            "reused_phrase_count": reused_phrase_count,
            "synthesized_phrase_count": synthesized_phrase_count,
            "source_builds": [str(Path(path)) for path in (reuse_from_builds or [])],
        },
        "sentences": rows,
    }
    errors = validate_sentence_timeline(script, manifest)
    if errors:
        raise ValueError("; ".join(errors))
    manifest_path = build_dir / "sentence_audio_manifest.json"
    temporary = manifest_path.with_suffix(".json.part")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(manifest_path)
    return master


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--audio-mode", choices=["fixture", "supertonic3"], default="supertonic3")
    parser.add_argument("--tts-url")
    parser.add_argument("--gap-sec", type=float, default=0.35)
    parser.add_argument("--reuse-existing", action="store_true")
    parser.add_argument("--reuse-from-build", type=Path, action="append", default=[])
    parser.add_argument(
        "--voice",
        default=None,
        help="SuperTonic3 voice code (e.g. M2). Overrides --voice-lock-id and "
        "the script's own voice_lock_id field. Omit to resolve from the "
        "script (recommended -- keeps the CLI honoring script_candidate.json's "
        "declared voice_lock_id instead of silently defaulting to M4).",
    )
    parser.add_argument(
        "--voice-lock-id",
        default=None,
        help="e.g. M2_WARM. Used only when --voice is not given; overrides "
        "the script's own voice_lock_id field.",
    )
    parser.add_argument("--speed", type=float, default=None)
    parser.add_argument("--total-step", type=int, default=None)
    args = parser.parse_args()
    build_sentence_audio_master(
        args.script,
        args.build,
        args.audio_mode,
        args.tts_url,
        args.gap_sec,
        reuse_existing=args.reuse_existing,
        reuse_from_builds=args.reuse_from_build,
        voice_lock_id=args.voice_lock_id,
        voice=args.voice,
        speed=args.speed,
        total_step=args.total_step,
    )


if __name__ == "__main__":
    main()

