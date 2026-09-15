# -*- coding: utf-8 -*-
"""Branding and HUD overlay module for Human Library video production.

Layers:
  1. Golden Watermark Emblem: Top-Right (W-w-30:30) with subtle alpha.
  2. Opening Laurel Wreath: 0~3s Center-Screen with 0.5s fade-out.
  3. Artifact HUD Cards: Bottom-Left (40:H-h-130) positioned above subtitle safe zone.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def build_branding_overlay_filtergraph(
    emblem_path: Path,
    wreath_path: Optional[Path] = None,
    hud1_path: Optional[Path] = None,
    hud2_path: Optional[Path] = None,
    base_video_label: str = "[v_base]",
    out_label: str = "[v_branded]",
) -> Tuple[List[str], str]:
    """Build FFmpeg input arguments and filtergraph string for branding overlays.

    Returns (additional_inputs, filtergraph_str).
    """
    inputs = []
    current_label = base_video_label
    filter_chains = []
    input_idx = 1  # 0 is base video

    # 1. Golden Emblem Watermark (Always Top-Right W-w-30:30)
    emblem_path = Path(emblem_path).resolve()
    if emblem_path.exists():
        inputs.extend(["-i", str(emblem_path)])
        next_label = f"[v_emb_{input_idx}]"
        filter_chains.append(
            f"{current_label}[{input_idx}:v]overlay=W-w-30:30:format=auto{next_label}"
        )
        current_label = next_label
        input_idx += 1

    # 2. Opening Laurel Wreath (0~3.0s, centered, fade-out at 2.5~3.0s)
    if wreath_path and Path(wreath_path).exists():
        inputs.extend(["-i", str(Path(wreath_path).resolve())])
        next_label = f"[v_wreath_{input_idx}]"
        filter_chains.append(
            f"[{input_idx}:v]fade=t=out:st=2.5:d=0.5:alpha=1[wreath_faded];"
            f"{current_label}[wreath_faded]overlay=(W-w)/2:(H-h)/2-40:enable='between(t,0,3.0)':format=auto{next_label}"
        )
        current_label = next_label
        input_idx += 1

    # 3. Artifact HUD Card 1 (6.5s ~ 15.0s, Obsidian spearhead)
    if hud1_path and Path(hud1_path).exists():
        inputs.extend(["-i", str(Path(hud1_path).resolve())])
        next_label = f"[v_hud1_{input_idx}]"
        filter_chains.append(
            f"[{input_idx}:v]fade=t=in:st=6.5:d=0.4:alpha=1,fade=t=out:st=14.5:d=0.5:alpha=1[hud1_faded];"
            f"{current_label}[hud1_faded]overlay=40:H-h-130:enable='between(t,6.5,15.0)':format=auto{next_label}"
        )
        current_label = next_label
        input_idx += 1

    # 4. Artifact HUD Card 2 (40.0s ~ 55.0s, EPAS1 gene)
    if hud2_path and Path(hud2_path).exists():
        inputs.extend(["-i", str(Path(hud2_path).resolve())])
        next_label = f"[v_hud2_{input_idx}]"
        filter_chains.append(
            f"[{input_idx}:v]fade=t=in:st=40.0:d=0.4:alpha=1,fade=t=out:st=54.5:d=0.5:alpha=1[hud2_faded];"
            f"{current_label}[hud2_faded]overlay=40:H-h-130:enable='between(t,40.0,55.0)':format=auto{next_label}"
        )
        current_label = next_label
        input_idx += 1

    # Final rename to out_label
    if current_label != out_label:
        filter_chains.append(f"{current_label}null{out_label}")

    filtergraph = ";".join(filter_chains)
    return inputs, filtergraph
