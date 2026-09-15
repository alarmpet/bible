# -*- coding: utf-8 -*-
"""Content-aware Ken Burns / motion renderer v3.

Replaces `build_motion_clips_v2.py` and `smooth_subpixel_motion_engine.py`'s core
trajectory math. Implements Aug26 Task 8
(docs/superpowers/plans/2026-08-26-human-archive-script-image-motion-upgrade.md) and
Hard Gate 5 (docs/orchestration/HARD_GATES.md).

What was wrong, measured (2026-08-26 diagnosis, reconfirmed 2026-09-15 against the
current code):
- Both legacy engines apply a single cosine ease-in/ease-out ("S-curve") across the
  ENTIRE shot duration. A cosine's derivative is ~0 at both ends, so for a 6-12s shot,
  the first and last 1-2 seconds have almost no visible pixel movement -- measured
  78-84% near-duplicate frames (ffmpeg `mpdecimate`) on real output.
- `build_motion_clips_v2.py` additionally: a `SHOT_MOTION_MAP` keyed by IDs
  (`ch1_001`) that don't match real shot IDs (`ha002_v6_shot_001`), so 100% of shots
  fall through to a 4-preset `index % 4` rotation with no connection to content; three
  differently-named presets computing the identical crop formula; and a `tilt_up` preset
  whose crop offset goes 0 -> peak -> 0 (an unintended direction reversal) because
  `max_dy(t)` (increasing) is multiplied by `(1 - ease(t))` (decreasing).

This module fixes the trajectory math (`ease_ramp_cruise`, `MotionKeyframe`
interpolation: short eased ramps at each end, constant velocity in the middle, so a
12-second push-in moves visibly for all 12 seconds, not just the middle third) and
replaces named-preset lookup with an explicit `motion_intent` (matching
`episode_visual_contract.scenes[].motion_intent` in the Aug26 design) -- there is no ID
keying to silently mismatch, and no two motion_intents can compute the same formula
because there is exactly one formula, parameterized by start/end keyframes.
"""
from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional

from PIL import Image

# ---------------------------------------------------------------------------------
# Easing: short ramp-in / constant cruise / short ramp-out, not a single S-curve.
# ---------------------------------------------------------------------------------

DEFAULT_RAMP_FRAC = 0.15  # each ramp is at most 15% of the shot; Aug26 asked for a
# fixed 0.2-0.4s ramp, but a duration-independent fraction keeps very short pilot shots
# (2.5s) and very long outro shots (12.5s) both correctly dominated by the cruise phase.


def ease_ramp_cruise(t: float, ramp_frac: float = DEFAULT_RAMP_FRAC) -> float:
    """Position in [0, 1] for normalized time t in [0, 1].

    Velocity profile: a quarter-sine ramp-in over [0, r], constant velocity ("cruise")
    over [r, 1-r], a symmetric quarter-sine ramp-out over [1-r, 1]. Velocity is
    continuous at both boundaries (no visible speed jump/jerk), and velocity during the
    cruise phase is constant and non-zero for the whole middle of the shot -- this is
    the fix for the "near-zero velocity for most of the shot" defect a single full-shot
    cosine produces.

    ramp_frac=0 degenerates to pure linear (constant-velocity) motion, which is a valid
    and often-fine choice; it is not treated as a special case needing ramps at all.
    """
    t = max(0.0, min(1.0, float(t)))
    r = max(0.0, min(0.49, float(ramp_frac)))
    if r < 1e-9:
        return t

    ramp_area = 2.0 * r / math.pi          # distance covered by one quarter-sine ramp
    cruise_area = max(0.0, 1.0 - 2.0 * r)  # distance covered by the constant-velocity middle
    total = 2.0 * ramp_area + cruise_area

    if t <= r:
        pos = ramp_area * (1.0 - math.cos(math.pi * t / (2.0 * r)))
    elif t <= 1.0 - r:
        pos = ramp_area + (t - r)
    else:
        remaining = 1.0 - t
        pos = total - ramp_area * (1.0 - math.cos(math.pi * remaining / (2.0 * r)))

    return max(0.0, min(1.0, pos / total))


# ---------------------------------------------------------------------------------
# Trajectory: normalized (zoom, center_x, center_y) keyframes, linearly interpolated
# through the eased position -- monotonic by construction, so a direction-reversal bug
# like the legacy `tilt_up` (0 -> peak -> 0) cannot occur: each axis is a straight
# interpolation between two fixed values, never a product of two independently-moving
# functions.
# ---------------------------------------------------------------------------------

@dataclass(frozen=True)
class MotionKeyframe:
    zoom: float = 1.0        # >= 1.0; 1.0 = no crop (full frame)
    center_x: float = 0.5    # normalized crop-center position, 0..1
    center_y: float = 0.5


def interpolate(start: MotionKeyframe, end: MotionKeyframe, t_frac: float,
                 ramp_frac: float = DEFAULT_RAMP_FRAC) -> MotionKeyframe:
    """The single trajectory formula every motion_intent uses. Two motion_intents can
    only produce different output by having different start/end keyframes -- there is
    no second formula for a differently-named preset to accidentally duplicate."""
    p = ease_ramp_cruise(t_frac, ramp_frac)
    return MotionKeyframe(
        zoom=start.zoom + (end.zoom - start.zoom) * p,
        center_x=start.center_x + (end.center_x - start.center_x) * p,
        center_y=start.center_y + (end.center_y - start.center_y) * p,
    )


def compute_crop_box(canvas_w: float, canvas_h: float, target_w: float, target_h: float,
                      kf: MotionKeyframe) -> tuple[float, float, float, float]:
    """Subpixel crop box (left, top, right, bottom) as floats -- no integer
    quantization, matching the one part of the legacy engines that was already correct."""
    crop_w = target_w / kf.zoom
    crop_h = target_h / kf.zoom
    left = (canvas_w - crop_w) * kf.center_x
    top = (canvas_h - crop_h) * kf.center_y
    return left, top, left + crop_w, top + crop_h


# ---------------------------------------------------------------------------------
# motion_intent -> start/end keyframes. Duration- and magnitude-aware: the legacy
# engine used the same ~3.5% zoom delta regardless of shot length, so a 27-second shot
# and a 4-second shot moved at wildly different (and for the long shot, imperceptible)
# on-screen speeds. Here the magnitude is chosen so the cruise-phase on-screen velocity
# clears a minimum px/frame threshold regardless of duration, up to a maximum sane bound.
# ---------------------------------------------------------------------------------

MOTION_INTENTS = ("static", "push_in", "pull_out", "pan_left", "pan_right",
                   "tilt_up", "tilt_down", "detail_crop")

MIN_CRUISE_PX_PER_FRAME = 0.8   # keep motion visible frame-to-frame at 25fps
MAX_ZOOM = 1.6                  # never crop in so far detail looks obviously blown up


def _zoom_delta_for_duration(duration_sec: float, fps: int, width: int,
                              base_delta: float, max_delta: float = 0.5) -> float:
    """Pick a zoom delta whose cruise-phase edge displacement clears
    MIN_CRUISE_PX_PER_FRAME for this shot's actual frame count, instead of reusing one
    constant delta for every duration (the legacy engines' bug: a 27s shot and a 4s
    shot moved at the same total zoom ratio, so the long shot's per-frame motion was
    imperceptible). A zoom delta d changes crop width by roughly d/(1+d) in normalized
    terms at zoom~1, which for the small d values used here is well approximated by d.
    """
    total_frames = max(1, round(duration_sec * fps))
    cruise_frames = max(1, total_frames * (1.0 - 2.0 * DEFAULT_RAMP_FRAC))
    needed_delta = (MIN_CRUISE_PX_PER_FRAME * cruise_frames) / float(width)
    return max(base_delta, min(max_delta, needed_delta))


def resolve_motion_keyframes(
    motion_intent: str,
    duration_sec: float,
    fps: int = 25,
    width: int = 1920,
    focal_anchor: Optional[tuple[float, float]] = None,
) -> tuple[MotionKeyframe, MotionKeyframe]:
    """Return (start, end) keyframes for a motion_intent. `focal_anchor` (normalized
    x, y) overrides the default frame-center target for push_in/pull_out/detail_crop
    when a scene's actual subject position is known; falls back to center otherwise.
    """
    intent = motion_intent if motion_intent in MOTION_INTENTS else "static"
    anchor_x, anchor_y = focal_anchor if focal_anchor else (0.5, 0.5)

    if intent == "static":
        return MotionKeyframe(), MotionKeyframe()

    if intent == "push_in":
        d = _zoom_delta_for_duration(duration_sec, fps, width, base_delta=0.10)
        return (MotionKeyframe(1.0, anchor_x, anchor_y),
                MotionKeyframe(1.0 + d, anchor_x, anchor_y))

    if intent == "pull_out":
        d = _zoom_delta_for_duration(duration_sec, fps, width, base_delta=0.10)
        return (MotionKeyframe(1.0 + d, anchor_x, anchor_y),
                MotionKeyframe(1.0, anchor_x, anchor_y))

    if intent == "detail_crop":
        d = _zoom_delta_for_duration(duration_sec, fps, width, base_delta=0.25)
        d = min(d, MAX_ZOOM - 1.0)
        return (MotionKeyframe(1.05, 0.5, 0.5),
                MotionKeyframe(min(MAX_ZOOM, 1.05 + d), anchor_x, anchor_y))

    if intent in ("pan_left", "pan_right"):
        zoom = 1.10
        span = _zoom_delta_for_duration(duration_sec, fps, width, base_delta=0.22) * 1.4
        span = min(span, 0.9 / zoom)  # never let the crop run off the source edge
        half = span / 2.0
        if intent == "pan_left":
            return MotionKeyframe(zoom, 0.5 + half, 0.5), MotionKeyframe(zoom, 0.5 - half, 0.5)
        return MotionKeyframe(zoom, 0.5 - half, 0.5), MotionKeyframe(zoom, 0.5 + half, 0.5)

    if intent in ("tilt_up", "tilt_down"):
        zoom = 1.10
        span = _zoom_delta_for_duration(duration_sec, fps, width, base_delta=0.22) * 1.4
        span = min(span, 0.9 / zoom)
        half = span / 2.0
        if intent == "tilt_up":
            return MotionKeyframe(zoom, 0.5, 0.5 + half), MotionKeyframe(zoom, 0.5, 0.5 - half)
        return MotionKeyframe(zoom, 0.5, 0.5 - half), MotionKeyframe(zoom, 0.5, 0.5 + half)

    return MotionKeyframe(), MotionKeyframe()  # unreachable given the intent clamp above


# ---------------------------------------------------------------------------------
# Rendering. Lossless (FFV1/MKV) intermediate by default: the legacy pipeline encoded
# H.264 once per motion clip and then AGAIN at final subtitle burn-in/concat, and
# CRF-18 H.264 is lossy both times. This renderer's own encode is the only one that
# should ever be lossy, and by default it isn't -- the final delivery encode belongs to
# render_episode_v2.py's single mux step.
# ---------------------------------------------------------------------------------

def load_source_canvas(image_path: Path, min_width: int, min_height: int) -> Image.Image:
    """Load the source at its native resolution -- never pre-downscale to the output
    size before cropping, which is what threw away overscan headroom in
    `build_motion_clips_v2.py`. If the source is smaller than the output frame, upscale
    with Lanczos (still better than the legacy behavior of forcing exactly 1920x1080
    and then cropping into that already-lossy frame) and this is reported by the
    caller, not silently hidden.
    """
    with Image.open(image_path) as img:
        src = img.convert("RGB")
        if src.width < min_width or src.height < min_height:
            scale = max(min_width / src.width, min_height / src.height)
            src = src.resize((max(min_width, round(src.width * scale)),
                               max(min_height, round(src.height * scale))),
                              Image.Resampling.LANCZOS)
        return src.copy()


def render_motion_clip_v3(
    image_path: Path,
    output_path: Path,
    duration_sec: float,
    motion_intent: str = "static",
    fps: int = 25,
    width: int = 1920,
    height: int = 1080,
    focal_anchor: Optional[tuple[float, float]] = None,
    ramp_frac: float = DEFAULT_RAMP_FRAC,
    lossless: bool = True,
) -> Path:
    """Render one shot's motion clip. `lossless=True` (default) writes FFV1-in-MKV; set
    False only for quick local previews, never for a build that will ship."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    total_frames = max(1, round(duration_sec * fps))

    canvas = load_source_canvas(image_path, width, height)
    canvas_w, canvas_h = float(canvas.width), float(canvas.height)

    start_kf, end_kf = resolve_motion_keyframes(motion_intent, duration_sec, fps, width,
                                                 focal_anchor)

    if lossless:
        codec_args = ["-c:v", "ffv1", "-level", "3", "-g", "1", "-pix_fmt", "yuv420p"]
    else:
        codec_args = ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
                      "-pix_fmt", "yuv420p"]

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(fps),
        "-i", "-",
        *codec_args,
        "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709",
        "-color_trc", "bt709",
        str(output_path),
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for frame_idx in range(total_frames):
            t_frac = frame_idx / max(1, total_frames - 1)
            kf = interpolate(start_kf, end_kf, t_frac, ramp_frac)
            box = compute_crop_box(canvas_w, canvas_h, float(width), float(height), kf)
            frame = canvas.resize((width, height), resample=Image.Resampling.BICUBIC, box=box)
            proc.stdin.write(frame.tobytes())
    finally:
        proc.stdin.close()
        ret = proc.wait()
    if ret != 0:
        raise RuntimeError(f"FFmpeg failed rendering motion clip for {image_path} (exit {ret})")
    return output_path
