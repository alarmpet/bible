# -*- coding: utf-8 -*-
"""Provider adapter for Google Flow and test card fixtures with strict lineage and fail-closed timeout."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.provenance import compute_file_sha256, compute_object_sha256


class FlowProviderAdapter:
    """Manages generation and asset download with explicit card ID binding."""

    def __init__(self, mode: str = "fixture", cdp_url: str = "http://127.0.0.1:9222"):
        self.mode = mode
        self.cdp_url = cdp_url

    def generate_shot_asset(
        self,
        shot: dict[str, Any],
        output_dir: Path,
        fixture_cards: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate or retrieve asset bound strictly to prompt and card ID."""
        shot_id = shot["shot_id"]
        order = shot["order"]
        vis = shot.get("visual", {})
        prompt_text = f"{vis.get('place')}, {vis.get('era')}, {', '.join(vis.get('subject', []))}, {', '.join(vis.get('action', []))}, {vis.get('tone')}"
        prompt_sha = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest().upper()

        output_dir.mkdir(parents=True, exist_ok=True)
        final_img_path = output_dir / f"{shot_id}.jpg"
        part_img_path = output_dir / f"{shot_id}.jpg.part"

        if self.mode == "fixture":
            card_info = (fixture_cards or {}).get(shot_id)
            if not card_info or card_info.get("status") == "TIMEOUT":
                return {
                    "shot_id": shot_id,
                    "order": order,
                    "card_id": card_info.get("card_id", "CARD-TIMEOUT") if card_info else "CARD-NOT-FOUND",
                    "prompt_sha256": prompt_sha,
                    "file_path": "",
                    "sha256": "",
                    "bytes": 0,
                    "width": 0,
                    "height": 0,
                    "status": "TIMEOUT",
                }

            # Create rich 1920x1080 Joseon Cinematic Ink-Wash Chiaroscuro Art with distinct perceptual hashes
            # Use order-derived distinct primary background and composition
            img = Image.new("RGB", (1920, 1080), color=(10, 13, 18))
            draw = ImageDraw.Draw(img)

            # 1. Broad distinct color fields per quadrant based on order bits
            for qx in range(4):
                for qy in range(3):
                    q_val = ((order * 79 + qx * 127 + qy * 193) % 180) + 15
                    q_col = (
                        (q_val * 37 + order * 13) % 120 + 10,
                        (q_val * 53 + order * 29) % 110 + 10,
                        (q_val * 71 + order * 47) % 130 + 15
                    )
                    draw.rectangle([qx * 480, qy * 360, (qx + 1) * 480, (qy + 1) * 360], fill=q_col)

            # 2. Distinct dominant compositional geometry per shot
            geom_type = order % 5
            amber_gold = (212, 175, 55)
            crimson_red = (178, 34, 34)
            teal_dark = (30, 58, 76)

            if geom_type == 0:
                # Mountain ridge / Horizon
                pts = [(0, 700 + (order * 17) % 200)]
                for sx in range(0, 1950, 180):
                    pts.append((sx, 400 + ((order * 59 + sx * 23) % 350)))
                pts.extend([(1920, 1080), (0, 1080)])
                draw.polygon(pts, fill=teal_dark, outline=amber_gold, width=4)
            elif geom_type == 1:
                # Royal Pavilion / Temple roof
                cx = 400 + (order * 89) % 1100
                cy = 350 + (order * 47) % 300
                roof = [
                    (cx - 350, cy + 180), (cx - 220, cy - 80), (cx, cy - 180),
                    (cx + 220, cy - 80), (cx + 350, cy + 180),
                    (cx + 250, cy + 220), (cx - 250, cy + 220)
                ]
                draw.polygon(roof, fill=crimson_red, outline=amber_gold, width=4)
            elif geom_type == 2:
                # Arched moon gate / circular celestial mandala
                cx = 500 + (order * 103) % 900
                cy = 500 + (order * 61) % 200
                r = 220 + (order * 13) % 140
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=amber_gold, outline=(255, 255, 255), width=5)
                draw.ellipse([cx - r + 40, cy - r + 40, cx + r - 40, cy + r - 40], fill=(15, 20, 28))
            elif geom_type == 3:
                # Royal throne screen / vertical calligraphy columns
                for col_i in range(8):
                    lx = 200 + col_i * 200 + (order * 19) % 80
                    ly0 = 150 + ((order * 31 + col_i * 53) % 250)
                    ly1 = 950
                    draw.rectangle([lx, ly0, lx + 120, ly1], fill=((col_i * 45 + order * 30) % 180 + 20, 30, 45), outline=amber_gold, width=3)
            else:
                # Diagonal light shaft & Hanok lattice window
                for d_i in range(12):
                    dx0 = (order * 67 + d_i * 160) % 1920
                    draw.line([dx0, 0, dx0 + 400, 1080], fill=(212, 175, 55), width=8)

            # 3. High-frequency unique dot and particle constellation
            for p in range(50):
                px = (order * 389 + p * 233 + (p * p) * 17) % 1920
                py = (order * 281 + p * 197 + (p * p) * 29) % 1080
                pr = 3 + (p % 6)
                draw.ellipse([px - pr, py - pr, px + pr, py + pr], fill=((order * 50 + p * 20) % 255, (order * 80 + p * 10) % 255, 200))

            # 4. Seal Badge (붉은 낙관 인장 at bottom right)
            seal_x = 1750 - (order % 4) * 20
            seal_y = 920 - (order % 3) * 20
            draw.rectangle([seal_x, seal_y, seal_x + 90, seal_y + 90], fill=crimson_red, outline=(255, 255, 255), width=2)
            draw.rectangle([seal_x + 8, seal_y + 8, seal_x + 82, seal_y + 82], outline=amber_gold, width=2)

            img.save(part_img_path, format="JPEG", quality=95)

            # Atomic replace
            os.replace(part_img_path, final_img_path)

            file_sha = compute_file_sha256(final_img_path)
            stat = final_img_path.stat()

            return {
                "shot_id": shot_id,
                "order": order,
                "card_id": card_info.get("card_id", f"CARD-{shot_id}"),
                "prompt_sha256": prompt_sha,
                "file_path": final_img_path.name,
                "sha256": file_sha,
                "bytes": stat.st_size,
                "width": 1920,
                "height": 1080,
                "status": "COMPLETED",
            }

        # Real CDP Mode placeholder / implementation hook
        raise NotImplementedError("Live Playwright CDP generation requires active Chrome browser session")
