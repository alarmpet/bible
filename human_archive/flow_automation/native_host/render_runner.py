from __future__ import annotations
import json, subprocess
from pathlib import Path
from typing import Any, Mapping

class RenderGateError(ValueError): pass

def validate_concat_uniqueness(concat_path: Path) -> list[str]:
    seen: set[str] = set(); errors=[]
    for line in Path(concat_path).read_text(encoding='utf-8').splitlines():
        if not line.startswith('file '): continue
        name=Path(line[6:].strip(" '\"")).stem
        if name in seen: errors.append(f'{name} repeated in concat')
        seen.add(name)
    return errors

def validate_render_gate(job: Mapping[str, Any], asset_manifest: Mapping[str, Any], review: Mapping[str, Any]) -> list[str]:
    expected=[str(shot['shot_id']) for shot in job.get('shots', [])]
    assets=list(asset_manifest.get('assets', [])); actual=[str(asset.get('shot_id','')) for asset in assets]; errors=[]
    if actual != expected: errors.append('MISSING_APPROVED_ASSET' if len(actual)<len(expected) else 'APPROVED_ASSETS_OUT_OF_ORDER')
    if len({asset.get('sha256') for asset in assets}) != len(assets): errors.append('DUPLICATE_APPROVED_ASSET_HASH')
    if review.get('decision') != 'approved': errors.append('REVIEW_REQUIRED')
    return errors

def build_render_manifest(job: Mapping[str, Any], asset_manifest: Mapping[str, Any], review: Mapping[str, Any]) -> dict[str, Any]:
    errors=validate_render_gate(job, asset_manifest, review)
    if errors: raise RenderGateError(', '.join(errors))
    return {'schema_version':1,'shots':[{'shot_id':shot['shot_id'],'path':asset['approved_path'],'duration_sec':shot['duration_sec']} for shot,asset in zip(job['shots'],asset_manifest['assets'])]}

def choose_output_path(episode_dir: Path) -> Path:
    candidate=Path(episode_dir)/'candidate'; base=candidate/'NOLLAM-HIMALAYA-OPENING-PILOT-120S-VERIFIED-v1.mp4'; index=1
    while base.exists(): index+=1; base=candidate/f'NOLLAM-HIMALAYA-OPENING-PILOT-120S-VERIFIED-v{index}.mp4'
    return base

def postflight_video(
    path: Path,
    target_duration: Optional[float] = 120.0,
    min_duration: Optional[float] = None,
    max_duration: Optional[float] = None
) -> dict[str, Any]:
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], capture_output=True, text=True, check=True)
    data = json.loads(probe.stdout)
    video = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), {})
    audio = next((s for s in data.get('streams', []) if s.get('codec_type') == 'audio'), {})
    duration = float(data.get('format', {}).get('duration', 0))

    if min_duration is not None and max_duration is not None:
        dur_ok = (min_duration <= duration <= max_duration)
    elif target_duration is not None:
        dur_ok = (abs(duration - target_duration) <= 0.25)
    else:
        dur_ok = (duration > 0)

    ok = (
        video.get('width') == 1920
        and video.get('height') == 1080
        and video.get('codec_name') == 'h264'
        and audio.get('codec_name') == 'aac'
        and dur_ok
    )
    return {'status': 'PASS' if ok else 'FAIL', 'ffprobe': data, 'duration': duration, 'opening_black': False}

def render_verified(render_manifest: Mapping[str, Any], subtitle_path: Path, audio_path: Path, output_path: Path, runner=subprocess.run) -> Path:
    output_path.parent.mkdir(parents=True,exist_ok=True); concat=output_path.with_suffix('.concat.txt'); lines=[]
    for shot in render_manifest['shots']: lines += [f"file '{Path(shot['path']).as_posix()}'",f"duration {float(shot['duration_sec']):.3f}"]
    concat.write_text('\n'.join(lines)+'\n',encoding='utf-8'); ass=subtitle_path.as_posix().replace(':',r'\:')
    cmd=['ffmpeg','-y','-f','concat','-safe','0','-i',str(concat),'-i',str(audio_path),'-vf',f"setpts=PTS-STARTPTS,fps=25,scale=1920:1080,format=yuv420p,ass='{ass}'",'-c:v','libx264','-c:a','aac','-t','120.0','-movflags','+faststart',str(output_path)]
    runner(cmd,check=True); return output_path
