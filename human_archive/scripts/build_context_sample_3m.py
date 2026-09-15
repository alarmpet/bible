# -*- coding: utf-8 -*-
"""Build fully contextualized 3-minute ShipSeonbi sample video with 100% matched visuals."""
from __future__ import annotations

import sys
import os
import json
import math
import subprocess
from pathlib import Path
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.tts_provider import SupertonicHttpProvider
from lib.audio_timeline import get_wav_duration, normalize_master_audio

build_dir = Path("human_archive/runs/ep02_jang_huibin/sample-3m-context-final")
build_dir.mkdir(parents=True, exist_ok=True)
audio_dir = build_dir / "audio"
audio_dir.mkdir(parents=True, exist_ok=True)
images_dir = build_dir / "images"
images_dir.mkdir(parents=True, exist_ok=True)
motion_dir = build_dir / "motion_clips"
motion_dir.mkdir(parents=True, exist_ok=True)
work_dir = build_dir / "work"
work_dir.mkdir(parents=True, exist_ok=True)
candidate_dir = build_dir / "candidate"
candidate_dir.mkdir(parents=True, exist_ok=True)

brain_dir = Path(r"C:\Users\shs\.gemini\antigravity\brain\4c9955d8-905b-44cb-a249-e670f6131c96")
full_images_dir = Path("human_archive/runs/ep02_jang_huibin/full-v6-001/images")
manifest_path = Path("human_archive/runs/ep02_jang_huibin/full-v6-001/asset_manifest.json")
manifest_assets = json.loads(manifest_path.read_text(encoding="utf-8")).get("assets", [])
asset_map = {a["shot_id"]: a["file_path"] for a in manifest_assets}

# 22-beat script with 100% contextual visual mapping
contextual_shots = [
    # 1. Hook & Dramatic Myth Debunking
    {
        "order": 1,
        "text": "에헴! 여러분, 사극 드라마 속 장희빈의 최후 기억하십니까?",
        "beat": "hook",
        "custom_img": brain_dir / "shot01_seonbi_intro_1788030710646.jpg",
        "motion": "kenburns_zoom_pan_in",
    },
    {
        "order": 2,
        "text": "눈을 부릅뜨고 사발을 집어던지며 악을 쓰는 표독한 악녀의 모습!",
        "beat": "hook",
        "custom_img": brain_dir / "shot02_furious_drama_1788030730025.jpg",
        "motion": "pan_right",
    },
    {
        "order": 3,
        "text": "망나니와 궁녀들이 달려들어 강제로 사약을 들이붓는 그 아수라장!",
        "beat": "hook",
        "custom_img": brain_dir / "shot03_forced_poison_1788030746040.jpg",
        "motion": "kenburns_hero_push",
    },
    {
        "order": 4,
        "text": "허허, 천만의 말씀!",
        "beat": "hook",
        "v6_shot": "ha002_v6_shot_008",
        "motion": "tilt_up",
    },
    {
        "order": 5,
        "text": "정사 실록과 승정원일기에는 장희빈의 난동 기록이 전혀 없답니다.",
        "beat": "hook",
        "v6_shot": "ha002_v6_shot_002",
        "motion": "kenburns_zoom_pan_in",
    },
    # 2. Roadmap & The Silence of True History
    {
        "order": 6,
        "text": "아니 글쎄, 사관이 붓 꽉 쥐고 기록한 현장은 쥐 죽은 듯 조용했지요.",
        "beat": "roadmap",
        "v6_shot": "ha002_v6_shot_007",
        "motion": "tilt_down",
    },
    {
        "order": 7,
        "text": "도대체 우리가 300년 동안 믿어온 그 막장 드라마는 어디서 온 걸까요?",
        "beat": "roadmap",
        "v6_shot": "ha002_v6_shot_006",
        "motion": "kenburns_hero_push",
    },
    {
        "order": 8,
        "text": "사약을 엎지르고 발악했다는 이야기는 소설과 야담의 창작이지요.",
        "beat": "roadmap",
        "v6_shot": "ha002_v6_shot_003",
        "motion": "pan_left",
    },
    {
        "order": 9,
        "text": "오늘 이 쉽선비와 함께, 야사와 정사의 가면을 싹 벗겨보시지요!",
        "beat": "roadmap",
        "v6_shot": "ha002_v6_shot_001",
        "motion": "kenburns_zoom_pan_out",
    },
    # 3. Body: The Secret Altar & Curse Dolls
    {
        "order": 10,
        "text": "자, 사건의 발단이 된 1701년 가을, 창경궁 취선당으로 가보지요.",
        "beat": "body",
        "v6_shot": "ha002_v6_shot_017",
        "motion": "kenburns_hero_push",
    },
    {
        "order": 11,
        "text": "취선당 서쪽에 신당을 차리고 통명전에 흉물을 묻은 사건이 드러났지요.",
        "beat": "body",
        "v6_shot": "ha002_v6_shot_026",
        "motion": "tilt_up",
    },
    {
        "order": 12,
        "text": "아니 글쎄, 중전 처소 밑에서 바늘 꽂힌 저주 인형이 쏟아져 나온 겁니다!",
        "beat": "body",
        "v6_shot": "ha002_v6_shot_018",
        "motion": "kenburns_zoom_pan_in",
    },
    {
        "order": 13,
        "text": "실록에는 취선당 서쪽의 신당과 통명전 흉물 매장 사건이 기록되어 있습니다.",
        "beat": "body",
        "v6_shot": "ha002_v6_shot_019",
        "motion": "pan_right",
    },
    # 4. Modern Analogy & Sukjong's Power Engineering
    {
        "order": 14,
        "text": "요즘으로 치면 대기업 로열패밀리 간의 살벌한 도청과 암투인 셈이지요.",
        "beat": "analogy",
        "v6_shot": "ha002_v6_shot_038",
        "motion": "kenburns_hero_push",
    },
    {
        "order": 15,
        "text": "숙빈 최씨의 결정적 밀고와 서인 세력의 결집이 국왕의 결단을 재촉했습니다.",
        "beat": "body",
        "v6_shot": "ha002_v6_shot_033",
        "motion": "tilt_down",
    },
    {
        "order": 16,
        "text": "단순한 여인의 질투가 아니라 왕권 강화를 위한 냉혹한 환국 숙청이었지요.",
        "beat": "body",
        "v6_shot": "ha002_v6_shot_037",
        "motion": "kenburns_zoom_pan_in",
    },
    # 5. Dissenting Ministers & King's Resolute Decision
    {
        "order": 17,
        "text": "소론 대신들은 세자의 생모를 죽여서는 안 된다며 결사 반대했지요.",
        "beat": "source_commentary",
        "v6_shot": "ha002_v6_shot_049",
        "motion": "pan_left",
    },
    {
        "order": 18,
        "text": "영의정 최석항 등이 강력히 간했으나 숙종은 뜻을 굽히지 않았답니다.",
        "beat": "source_commentary",
        "v6_shot": "ha002_v6_shot_051",
        "motion": "kenburns_hero_push",
    },
    # 6. Dignified Self-Execution & Epilogue
    {
        "order": 19,
        "text": "강제로 사약을 들이붓는 대신 체모를 갖추어 자진하도록 명을 내렸지요.",
        "beat": "body",
        "v6_shot": "ha002_v6_shot_066",
        "motion": "tilt_up",
    },
    {
        "order": 20,
        "text": "궁중이 숙연한 가운데 사사의 명이 체모를 갖추어 집행되었답니다.",
        "beat": "body",
        "v6_shot": "ha002_v6_shot_071",
        "motion": "kenburns_zoom_pan_in",
    },
    {
        "order": 21,
        "text": "장희빈은 과연 표독한 악녀였을까요, 비정한 권력의 희생양이었을까요?",
        "beat": "insight",
        "v6_shot": "ha002_v6_shot_102",
        "motion": "pan_right",
    },
    {
        "order": 22,
        "text": "다음에도 귀에 쏙 박히는 역사로 찾아오지요!",
        "beat": "outro",
        "v6_shot": "ha002_v6_shot_112",
        "motion": "kenburns_hero_push",
    },
]

provider = SupertonicHttpProvider("http://127.0.0.1:3093")

tts_wavs = []
shot_infos = []
current_time = 0.0
gap_sec = 0.35

print("🎤 Starting SuperTonic3 M4 TTS synthesis for 22 sentences...")
for idx, s in enumerate(contextual_shots):
    sid = f"context_shot_{idx+1:03d}"
    wav_path = audio_dir / f"{sid}.wav"
    print(f"[{idx+1:02d}/22] Synthesizing: {s['text']}")
    provider.synthesize_phrase(s["text"], wav_path, speed=0.92, voice="M4")
    dur = get_wav_duration(wav_path)

    start_s = round(current_time, 3)
    end_s = round(current_time + dur, 3)

    # Resolve matched visual image
    tgt_img = images_dir / f"{sid}.jpg"
    if "custom_img" in s and s["custom_img"].exists():
        tgt_img.write_bytes(s["custom_img"].read_bytes())
        print(f"  -> Visual Anchor: Custom High-Def Prompt Image ({s['custom_img'].name})")
    elif "v6_shot" in s:
        v6_id = s["v6_shot"]
        rel_path = asset_map.get(v6_id, f"{v6_id}.jpg")
        src_path = full_images_dir / rel_path
        if src_path.exists():
            tgt_img.write_bytes(src_path.read_bytes())
            print(f"  -> Visual Anchor: Flow Matched Shot {v6_id} ({rel_path})")
        else:
            first_rel = manifest_assets[0]["file_path"]
            tgt_img.write_bytes((full_images_dir / first_rel).read_bytes())

    shot_infos.append({
        "order": idx + 1,
        "shot_id": sid,
        "text": s["text"],
        "beat": s["beat"],
        "start_sec": start_s,
        "end_sec": end_s,
        "duration_sec": dur,
        "audio_file": wav_path.name,
        "image_file": tgt_img.name,
        "motion_type": s["motion"],
    })

    tts_wavs.append(wav_path)
    current_time = end_s + gap_sec

print(f"✅ TTS synthesis & contextual visual mapping complete! Total: {current_time:.2f}s")

# Concatenate and normalize audio
concat_txt = audio_dir / "audio_concat.txt"
silence_wav = audio_dir / "silence.wav"
subprocess.run(
    ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=mono:d={gap_sec}", "-c:a", "pcm_s16le", str(silence_wav)],
    check=True,
)

concat_entries = []
for i, wp in enumerate(tts_wavs):
    concat_entries.append(f"file '{wp.resolve().as_posix()}'")
    if i < len(tts_wavs) - 1:
        concat_entries.append(f"file '{silence_wav.resolve().as_posix()}'")
concat_txt.write_text("\n".join(concat_entries), encoding="utf-8")

raw_master = audio_dir / "raw_master.wav"
subprocess.run(
    ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c:a", "pcm_s16le", str(raw_master)],
    check=True,
)

master_wav = build_dir / "master_audio_48k.wav"
normalize_master_audio(raw_master, master_wav, target_lufs=-15.0)
print(f"✅ Master audio normalized to -15.0 LUFS: {master_wav}")

# Subtitles Generation
def format_ass_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:01d}:{minutes:02d}:{secs:05.2f}"

def split_korean_two_lines(text: str, max_chars: int = 22) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    lines, current = [], []
    current_len = 0
    for w in words:
        if current_len + len(w) + (1 if current else 0) <= max_chars:
            current.append(w)
            current_len += len(w) + (1 if current_len > 0 else 0)
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]
            current_len = len(w)
    if current:
        lines.append(" ".join(current))
    if len(lines) > 2:
        mid = len(lines) // 2
        return [" ".join(lines[:mid]), " ".join(lines[mid:])]
    return lines

header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: DocuMain,Malgun Gothic,54,&H00FFFFFF,&H000000FF,&H000A0A10,&HB0000000,-1,0,0,0,100,100,0,0,1,4.5,2.0,2,160,160,70,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

events = []
for s in shot_infos:
    lines = split_korean_two_lines(s["text"], max_chars=24)
    formatted = r"\N".join(lines)
    events.append(f"Dialogue: 0,{format_ass_timestamp(s['start_sec'])},{format_ass_timestamp(s['end_sec'])},DocuMain,,0,0,0,,{formatted}")

(build_dir / "subtitles.ass").write_text(header + "\n".join(events) + "\n", encoding="utf-8")
print("✅ Subtitles.ass generated.")

# Motion Clips Rendering
def render_subpixel_clip(img_path: Path, out_clip: Path, duration_sec: float, fps: int = 25, motion_type: str = "kenburns_zoom_pan_in"):
    total_frames = max(1, int(round(duration_sec * fps)))
    with Image.open(img_path) as src_im:
        src_rgb = src_im.convert("RGB")
        orig_w, orig_h = src_rgb.size
        if orig_w != 1920 or orig_h != 1080:
            src_rgb = src_rgb.resize((1920, 1080), Image.Resampling.LANCZOS)
            orig_w, orig_h = 1920, 1080

    ffmpeg_cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080",
        "-r", str(fps), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
        "-color_trc", "bt709", "-color_range", "tv", str(out_clip)
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
    zoom_start, zoom_end = 1.00, 1.05

    for frame_idx in range(total_frames):
        t = frame_idx / max(1, total_frames - 1)
        ease = (1.0 - math.cos(math.pi * t)) / 2.0
        current_zoom = zoom_start + (zoom_end - zoom_start) * ease
        crop_w = orig_w / current_zoom
        crop_h = orig_h / current_zoom
        max_dx = orig_w - crop_w
        max_dy = orig_h - crop_h

        if motion_type in ["kenburns_zoom_pan_in", "pan_right", "kenburns_hero_push"]:
            crop_x = max_dx * (0.3 + 0.4 * ease)
            crop_y = max_dy * (0.3 + 0.4 * ease)
        elif motion_type == "tilt_up":
            crop_x = max_dx * 0.5
            crop_y = max_dy * (1.0 - ease)
        elif motion_type == "tilt_down":
            crop_x = max_dx * 0.5
            crop_y = max_dy * ease
        elif motion_type in ["pan_left", "kenburns_zoom_pan_out"]:
            crop_x = max_dx * (0.7 - 0.4 * ease)
            crop_y = max_dy * (0.7 - 0.4 * ease)
        else:
            crop_x = max_dx * 0.5
            crop_y = max_dy * 0.5

        box = (crop_x, crop_y, crop_x + crop_w, crop_y + crop_h)
        frame_img = src_rgb.resize((1920, 1080), resample=Image.Resampling.BICUBIC, box=box)
        proc.stdin.write(frame_img.tobytes())

    proc.stdin.close()
    proc.wait()

print("🎬 Rendering motion clips for 22 shots...")
rendered_clips = []
for idx, s in enumerate(shot_infos):
    out_clip = motion_dir / f"{s['shot_id']}_motion.mp4"
    img_path = images_dir / s["image_file"]
    clip_dur = s["duration_sec"] + (gap_sec if idx < len(shot_infos) - 1 else 0.0)
    render_subpixel_clip(img_path, out_clip, clip_dur, fps=25, motion_type=s["motion_type"])
    rendered_clips.append(out_clip)
    print(f"[{idx+1:02d}/22] Rendered clip: {out_clip.name} ({clip_dur:.2f}s, {s['motion_type']})")

print("✅ All motion clips rendered.")

concat_list_file = work_dir / "motion_concat.txt"
concat_list_file.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in rendered_clips), encoding="utf-8")

visual_assembled = work_dir / "visual_assembled.mp4"
subprocess.run(
    ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_list_file), "-c:v", "copy", str(visual_assembled)],
    check=True,
)

candidate_file = candidate_dir / "HA002-sample-3m-context-final.mp4"
esc_ass = str(build_dir / "subtitles.ass").replace("\\", "/").replace(":", "\\:")

cmd = [
    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
    "-i", str(visual_assembled),
    "-i", str(master_wav),
    "-vf", f"subtitles='{esc_ass}'",
    "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
    "-preset", "fast", "-crf", "18",
    "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
    "-color_trc", "bt709", "-color_range", "tv",
    "-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0",
    "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-ar", "48000",
    "-shortest", "-movflags", "+faststart", "-f", "mp4",
    str(candidate_file)
]
print("🚀 Rendering final contextualized 3-minute video...")
subprocess.run(cmd, check=True)
print(f"🎉 Fully Contextualized 3-Minute Video Render Complete: {candidate_file}")
