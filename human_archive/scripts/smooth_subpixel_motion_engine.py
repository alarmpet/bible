# -*- coding: utf-8 -*-
"""DEPRECATED 2026-09-15 -- do not use for new builds. Quarantined per
docs/superpowers/plans/2026-09-15-human-archive-nollam-script-visual-motion-multi-llm-overhaul-plan.md
Task 4: despite the docstring below claiming "zero pixel judder," `compute_trajectory()`'s
basic motions (push_in/pull_out/pan_*/tilt_*) apply a single cosine ease across the WHOLE
shot duration -- the exact defect measured at 78-84% near-duplicate frames elsewhere in
this repository, never actually measured here. Use `motion_engine_v3.py`
(scripts/build_motion_clips_v3.py for the CLI entrypoint) instead, which fixes the
trajectory math (short eased ramps at each end, constant velocity in between) and is
covered by an empirical cadence test (tests/test_motion_cadence.py: 0-3% near-duplicate
on the same ffmpeg mpdecimate measurement this repo's Aug26 diagnosis used). Kept here
read-only for audit/rollback (and because 3 legitimate production scripts --
run_san_jose_full_pipeline.py, run_san_jose_20min_flow_production.py,
run_neanderthal_full_pipeline.py -- still import it; migrating those call sites is a
follow-up, not yet done as of this notice).

Smooth Subpixel Motion Engine (Ken Burns Overhaul).

Eliminates 1-pixel stair-step judder and jerky linear movement:
1. Scales source image to a 2304x1296 (120% overscan) canvas using Lanczos.
2. Evaluates Cosine S-curve easing: smooth_t = 0.5 * (1.0 - math.cos(math.pi * t)).
3. Computes continuous floating-point crop boxes without integer quantization.
4. Performs subpixel Bicubic resampling in PIL with box=(left, top, right, bottom).
5. Pipes raw RGB frames into FFmpeg libx264 for artifact-free broadcast delivery.
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
from PIL import Image


def cosine_easing(t: float) -> float:
    """Compute S-curve ease-in-out using cosine.
    
    t in [0.0, 1.0] -> returns smooth_t in [0.0, 1.0] with zero derivative at endpoints.
    """
    clamped_t = max(0.0, min(1.0, float(t)))
    return 0.5 * (1.0 - math.cos(math.pi * clamped_t))


def compute_trajectory(
    frame: int,
    total_frames: int,
    motion: str = "push_in"
) -> Tuple[float, float, float]:
    """Return continuous floating-point (zoom, center_x, center_y) for the given frame.
    
    All coordinates are normalized in [0.0, 1.0], zoom is >= 1.0.
    """
    if motion in {"tri_phasic", "tri_phasic_ken_burns", "long_take_tri_phasic"}:
        return compute_tri_phasic_trajectory(frame, total_frames)
    if motion in {"biphasic_ken_burns", "biphasic_push_in"}:
        return compute_biphasic_trajectory(frame, total_frames, "push_in")
    if motion in {"layer3_perceptual_cut", "perceptual_cut"}:
        return compute_perceptual_cut_trajectory(frame, total_frames)
    if motion == "static" or total_frames <= 1:
        return 1.0, 0.5, 0.5

    linear_t = max(0.0, min(1.0, frame / float(total_frames - 1)))
    st = cosine_easing(linear_t)

    if motion == "push_in":
        zoom = 1.0 + 0.12 * st
        return zoom, 0.5, 0.5
    elif motion == "pull_out":
        zoom = 1.12 - 0.12 * st
        return zoom, 0.5, 0.5
    elif motion == "pan_left":
        zoom = 1.08
        x = 0.65 - 0.30 * st
        return zoom, x, 0.5
    elif motion == "pan_right":
        zoom = 1.08
        x = 0.35 + 0.30 * st
        return zoom, x, 0.5
    elif motion == "tilt_up":
        zoom = 1.08
        y = 0.65 - 0.30 * st
        return zoom, 0.5, y
    elif motion == "tilt_down":
        zoom = 1.08
        y = 0.35 + 0.30 * st
        return zoom, 0.5, y
    else:
        zoom = 1.0 + 0.08 * st
        return zoom, 0.5, 0.5


def compute_biphasic_trajectory(
    frame: int,
    total_frames: int,
    motion: str = "push_in",
    phase_ratio: float = 0.5,
) -> Tuple[float, float, float]:
    """Return a two-stage trajectory: ambient composition, then focal push-in.

    Stage one preserves spatial context with the requested movement.  Stage
    two settles at the visual center and gradually increases scale, making a
    long narration shot feel alive without introducing a hard cut.
    """
    if total_frames <= 1:
        return 1.0, 0.5, 0.5
    ratio = max(0.2, min(0.8, float(phase_ratio)))
    normalized = max(0.0, min(1.0, frame / float(total_frames - 1)))
    if normalized <= ratio:
        local_t = normalized / ratio
        eased = cosine_easing(local_t)
        if motion == "pan_left":
            return 1.04, 0.65 - 0.15 * eased, 0.5
        if motion == "pan_right":
            return 1.04, 0.35 + 0.15 * eased, 0.5
        if motion == "tilt_up":
            return 1.04, 0.5, 0.65 - 0.15 * eased
        if motion == "tilt_down":
            return 1.04, 0.5, 0.35 + 0.15 * eased
        return 1.0 + 0.04 * eased, 0.5, 0.5

    local_t = (normalized - ratio) / (1.0 - ratio)
    eased = cosine_easing(local_t)
    return 1.04 + 0.12 * eased, 0.5, 0.5


def compute_perceptual_cut_trajectory(
    frame: int,
    total_frames: int,
    fps: int = 25,
    cut_time_sec: float = 5.0,
) -> Tuple[float, float, float]:
    """Layer 3 Perceptual Cut trajectory: wide master before 5.0s, jump-cut close-up at 5.0s."""
    cut_frame = int(round(cut_time_sec * fps))
    if total_frames <= cut_frame:
        linear_t = max(0.0, min(1.0, frame / float(max(1, total_frames - 1))))
        return 1.0 + 0.10 * cosine_easing(linear_t), 0.5, 0.5

    if frame < cut_frame:
        local_t = frame / float(cut_frame)
        st = cosine_easing(local_t)
        return 1.02 + 0.04 * st, 0.5, 0.5
    else:
        rem_frames = total_frames - cut_frame
        local_t = (frame - cut_frame) / float(max(1, rem_frames - 1))
        st = cosine_easing(local_t)
        return 1.18 + 0.05 * st, 0.5, 0.45


def compute_tri_phasic_trajectory(
    frame: int,
    total_frames: int,
    focal_position: str = "center",
    clamped_for_subtitles: bool = True,
) -> Tuple[float, float, float]:
    """Return a 3-stage trajectory for Tier 3 long-takes: Ambient Drift -> Dynamic Approach -> Focal Lock.

    Phase 1 (0% to 35%): Ambient Drift (zoom ~1.01-1.04, subtle horizontal exploration).
    Phase 2 (35% to 70%): Dynamic Approach (zoom 1.05 -> 1.17, Cosine approach to focal center).
    Phase 3 (70% to 100%): Focal Lock & Breathe (zoom 1.17 -> 1.22 micro-creep, locked on focal subject).
    """
    if total_frames <= 1:
        return 1.0, 0.5, 0.5

    t = max(0.0, min(1.0, frame / float(total_frames - 1)))

    target_y = 0.45
    if focal_position == "upper":
        target_y = 0.35
    elif focal_position == "lower":
        target_y = 0.65

    if clamped_for_subtitles and target_y > 0.75:
        target_y = 0.75

    target_x = 0.50
    if focal_position == "left":
        target_x = 0.40
    elif focal_position == "right":
        target_x = 0.60

    if t <= 0.35:
        p = t / 0.35
        sp = 0.8 * p + 0.2 * (0.5 * (1.0 - math.cos(math.pi * p)))
        zoom = 1.01 + 0.04 * sp
        center_x = 0.58 - 0.16 * sp
        center_y = 0.50 + 0.03 * sp
    elif t <= 0.70:
        p = (t - 0.35) / 0.35
        sp = 0.5 * p + 0.5 * (0.5 * (1.0 - math.cos(math.pi * p)))
        zoom = 1.05 + 0.12 * sp
        start_x = 0.42
        center_x = start_x + (target_x - start_x) * sp
        center_y = 0.53 + (target_y - 0.53) * sp
    else:
        p = (t - 0.70) / 0.30
        sp = 0.8 * p + 0.2 * (0.5 * (1.0 - math.cos(math.pi * p)))
        zoom = 1.17 + 0.05 * sp
        center_x = target_x + 0.015 * math.sin(p * math.pi * 3)
        center_y = target_y + 0.010 * math.cos(p * math.pi * 3)

    if clamped_for_subtitles and center_y > 0.75:
        center_y = 0.75

    return zoom, center_x, center_y


def compute_crop_box(
    canvas_w: float,
    canvas_h: float,
    target_w: float,
    target_h: float,
    zoom: float,
    norm_x: float,
    norm_y: float
) -> Tuple[float, float, float, float]:
    """Calculate subpixel crop box (left, top, right, bottom) as floating-point floats."""
    crop_w = target_w / zoom
    crop_h = target_h / zoom
    left = (canvas_w - crop_w) * norm_x
    top = (canvas_h - crop_h) * norm_y
    right = left + crop_w
    bottom = top + crop_h
    return left, top, right, bottom


def prepare_overscan_canvas(
    image_path: Path,
    canvas_w: int = 2304,
    canvas_h: int = 1296
) -> Image.Image:
    """Load and center image onto overscan canvas using high quality Lanczos filter."""
    with Image.open(image_path) as img:
        src = img.convert("RGB")
        # Resize to fit inside or fill overscan canvas maintaining aspect ratio
        src_aspect = src.width / src.height
        canvas_aspect = canvas_w / canvas_h
        
        if abs(src_aspect - canvas_aspect) < 1e-3:
            scaled = src.resize((canvas_w, canvas_h), Image.Resampling.LANCZOS)
            return scaled
        else:
            # Aspect fill
            if src_aspect > canvas_aspect:
                new_h = canvas_h
                new_w = int(round(canvas_h * src_aspect))
            else:
                new_w = canvas_w
                new_h = int(round(canvas_w / src_aspect))
            scaled = src.resize((new_w, new_h), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
            offset_x = (canvas_w - new_w) // 2
            offset_y = (canvas_h - new_h) // 2
            canvas.paste(scaled, (offset_x, offset_y))
            return canvas


def render_smooth_motion_clip(
    image_path: Path,
    output_path: Path,
    duration: float,
    motion: str = "push_in",
    fps: int = 25,
    width: int = 1920,
    height: int = 1080
) -> Path:
    """Render an ultra-smooth subpixel Ken Burns video clip with zero pixel judder."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames = max(1, round(duration * fps))

    canvas_w = int(round(width * 1.2))
    canvas_h = int(round(height * 1.2))
    canvas = prepare_overscan_canvas(image_path, canvas_w=canvas_w, canvas_h=canvas_h)

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-color_range", "tv",
        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        str(output_path)
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None

    for f in range(frames):
        zoom, norm_x, norm_y = compute_trajectory(f, frames, motion)
        left, top, right, bottom = compute_crop_box(
            canvas_w=float(canvas_w),
            canvas_h=float(canvas_h),
            target_w=float(width),
            target_h=float(height),
            zoom=zoom,
            norm_x=norm_x,
            norm_y=norm_y
        )
        rendered = canvas.resize(
            (width, height),
            resample=Image.Resampling.BICUBIC,
            box=(left, top, right, bottom)
        )
        proc.stdin.write(rendered.tobytes())

    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"FFmpeg failed while rendering smooth clip for {image_path}")

    return output_path


def check_trajectory_static_hold(
    trajectory_points: List[Tuple[float, float, float]],
    canvas_w: float = 2304.0,
    canvas_h: float = 1296.0,
    target_w: float = 1920.0,
    target_h: float = 1080.0,
    window_size: int = 25,
    min_displacement_px: float = 3.0,
) -> bool:
    """Check whether any sliding window of `window_size` frames has displacement < min_displacement_px.

    Returns True if trajectory passes (continuous motion, no static hold).
    Returns False if a static dead zone is detected.
    """
    n = len(trajectory_points)
    if n <= window_size:
        return True

    crop_boxes = [
        compute_crop_box(canvas_w, canvas_h, target_w, target_h, zoom, nx, ny)
        for zoom, nx, ny in trajectory_points
    ]

    for i in range(n - window_size):
        c1 = crop_boxes[i]
        c2 = crop_boxes[i + window_size]
        dx = c2[0] - c1[0]
        dy = c2[1] - c1[1]
        dw = (c2[2] - c2[0]) - (c1[2] - c1[0])
        dh = (c2[3] - c2[1]) - (c1[3] - c1[1])
        disp = math.sqrt(dx * dx + dy * dy + dw * dw + dh * dh)
        if disp < min_displacement_px:
            return False

    return True


def render_composite_opening_clip(
    output_path: Path,
    image_paths: Optional[List[Path]] = None,
    cuts: Optional[List[Dict[str, Any]]] = None,
    duration: float = 11.0,
    fps: int = 25,
    width: int = 1920,
    height: int = 1080,
    dissolve_frames: int = 6,
) -> Path:
    """Render a 3-cut visible FLOW opening composite clip into a single MP4 rawvideo pipe.

    Uses PIL in-memory frame switching and 6-frame cross-dissolve with strict monotonic PTS.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if cuts is None:
        if not image_paths or len(image_paths) != 3:
            raise ValueError("Must provide either `cuts` or exactly 3 `image_paths` for opening composite.")
        d1 = duration * (3.0 / 11.0)
        d2 = duration * (3.5 / 11.0)
        d3 = duration - d1 - d2
        cuts = [
            {"image_path": Path(image_paths[0]), "duration": d1, "motion": "pan_right", "visual_role": "context_wide"},
            {"image_path": Path(image_paths[1]), "duration": d2, "motion": "push_in", "visual_role": "subject_action"},
            {"image_path": Path(image_paths[2]), "duration": d3, "motion": "push_in", "visual_role": "evidence_detail"},
        ]

    canvas_w = int(round(width * 1.2))
    canvas_h = int(round(height * 1.2))

    canvases = [
        prepare_overscan_canvas(Path(c["image_path"]), canvas_w=canvas_w, canvas_h=canvas_h)
        for c in cuts
    ]

    total_frames = max(1, round(sum(float(c.get("duration", 0.0)) for c in cuts) * fps))

    # Calculate cut frame counts
    cut_frame_counts = []
    accum = 0
    for idx, c in enumerate(cuts):
        if idx == len(cuts) - 1:
            cnt = total_frames - accum
        else:
            cnt = max(1, round(float(c.get("duration", 0.0)) * fps))
            accum += cnt
        cut_frame_counts.append(cnt)

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-color_range", "tv",
        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        str(output_path)
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None

    def _render_frame(cut_idx: int, local_f: int, local_cnt: int) -> Image.Image:
        c = cuts[cut_idx]
        motion = c.get("motion", "push_in")
        zoom, norm_x, norm_y = compute_trajectory(local_f, local_cnt, motion)
        left, top, right, bottom = compute_crop_box(
            canvas_w=float(canvas_w),
            canvas_h=float(canvas_h),
            target_w=float(width),
            target_h=float(height),
            zoom=zoom,
            norm_x=norm_x,
            norm_y=norm_y
        )
        return canvases[cut_idx].resize(
            (width, height),
            resample=Image.Resampling.BICUBIC,
            box=(left, top, right, bottom)
        )

    # Frame rendering loop with boundary dissolve
    cut_starts = []
    s = 0
    for cnt in cut_frame_counts:
        cut_starts.append(s)
        s += cnt

    for f in range(total_frames):
        # Determine active cut
        active_cut = 0
        for i in range(len(cuts)):
            if f >= cut_starts[i]:
                active_cut = i
        local_f = f - cut_starts[active_cut]
        local_cnt = cut_frame_counts[active_cut]

        rendered = _render_frame(active_cut, local_f, local_cnt)

        # Check if transitioning to next cut
        if active_cut < len(cuts) - 1:
            frames_to_next = cut_starts[active_cut + 1] - f
            if 0 < frames_to_next <= dissolve_frames:
                next_cut = active_cut + 1
                next_local_f = dissolve_frames - frames_to_next
                next_local_cnt = cut_frame_counts[next_cut]
                next_rendered = _render_frame(next_cut, next_local_f, next_local_cnt)
                alpha = (dissolve_frames - frames_to_next + 1) / float(dissolve_frames + 1)
                rendered = Image.blend(rendered, next_rendered, alpha)

        proc.stdin.write(rendered.tobytes())

    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"FFmpeg failed while rendering composite opening clip to {output_path}")

    return output_path


def render_perceptual_cut_subscenes(
    image_path: Path,
    output_path: Path,
    duration: float,
    fps: int = 25,
    width: int = 1920,
    height: int = 1080,
    cut_time_sec: float = 5.0,
) -> Path:
    """Render a Tier 1 perceptual subcut scene: wide establishing frame switching to tight crop at cut_time_sec.

    Keeps master speech/audio/subtitles 100% intact while generating a broadcast jump cut via PIL 120% overscan.
    """
    return render_smooth_motion_clip(
        image_path=image_path,
        output_path=output_path,
        duration=duration,
        motion="perceptual_cut",
        fps=fps,
        width=width,
        height=height,
    )


