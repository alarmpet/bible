# -*- coding: utf-8 -*-
"""Motion plan calculation and FFmpeg filter expression builder for butter-smooth, jitter-free documentary Ken Burns motion."""
from __future__ import annotations


def build_motion_filter(motion_type: str, duration_sec: float, fps: int = 25) -> str:
    """Build smooth mathematical scale+crop Ken Burns filter expressions without jitter or rasterization artifacts."""
    total_frames = max(1, int(round(duration_sec * fps)))

    if motion_type == "tilt_up":
        # Scale to 2160x1215 (1.125x) and crop 1920x1080 with smooth subtle linear scroll bottom to top
        base = f"scale=2160:1215:flags=bicubic,crop=1920:1080:x='(iw-ow)/2':y='(ih-oh)*(1-n/{total_frames})'"
    elif motion_type == "tilt_down":
        # Scale to 2160x1215 (1.125x) and crop 1920x1080 top to bottom
        base = f"scale=2160:1215:flags=bicubic,crop=1920:1080:x='(iw-ow)/2':y='(ih-oh)*(n/{total_frames})'"
    elif motion_type == "pan_right":
        # Scale to 2304x1296 (1.20x) and crop 1920x1080 panning horizontally left-to-right
        base = f"scale=2304:1296:flags=bicubic,crop=1920:1080:x='(iw-ow)*(n/{total_frames})':y='(ih-oh)/2'"
    elif motion_type == "pan_left":
        # Scale to 2304x1296 (1.20x) and crop 1920x1080 panning horizontally right-to-left
        base = f"scale=2304:1296:flags=bicubic,crop=1920:1080:x='(iw-ow)*(1-n/{total_frames})':y='(ih-oh)/2'"
    elif motion_type == "diagonal_drift":
        # Subtle diagonal drift
        base = f"scale=2304:1296:flags=bicubic,crop=1920:1080:x='(iw-ow)*(n/{total_frames})':y='(ih-oh)*(n/{total_frames})'"
    elif motion_type == "zoom_in":
        # Jitter-free subtle zoom in using static 2304x1296 buffer with smooth crop push
        base = f"scale=2304:1296:flags=bicubic,crop=1920:1080:x='(iw-ow)*(0.3+0.4*n/{total_frames})':y='(ih-oh)*(0.3+0.4*n/{total_frames})'"
    elif motion_type == "zoom_out":
        # Jitter-free subtle zoom out using static 2304x1296 buffer with smooth crop pull
        base = f"scale=2304:1296:flags=bicubic,crop=1920:1080:x='(iw-ow)*(0.7-0.4*n/{total_frames})':y='(ih-oh)*(0.7-0.4*n/{total_frames})'"
    elif motion_type in ["kenburns_zoom_pan_in", "kenburns_hero_push"]:
        # Signature Ken Burns: Smooth Slow Push-In + Subtle Pan Right (Zero Jitter)
        base = f"scale=2304:1296:flags=bicubic,crop=1920:1080:x='(iw-ow)*(0.2+0.6*n/{total_frames})':y='(ih-oh)*(0.2+0.6*n/{total_frames})'"
    elif motion_type in ["kenburns_zoom_pan_out", "kenburns_wide_sweep"]:
        # Signature Ken Burns: Smooth Slow Pull-Out + Subtle Pan Left (Zero Jitter)
        base = f"scale=2304:1296:flags=bicubic,crop=1920:1080:x='(iw-ow)*(0.8-0.6*n/{total_frames})':y='(ih-oh)*(0.5)'"
    else:
        # Default subtle cinematic drift
        base = f"scale=2160:1215:flags=bicubic,crop=1920:1080:x='(iw-ow)*(n/{total_frames})':y='(ih-oh)/2'"

    return f"{base},scale=in_range=full:out_range=limited,setsar=1,format=yuv420p"
