from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from lib.provenance import compute_file_sha256


CANONICAL_HOST_ASSET = "human_archive/assets/doodle_seonbi_v1.png"
CANONICAL_HOST_COSTUME = "white dopo with full torso, sleeves, collar, and waist tie"

# Profiles where host avatar overlay is strictly forbidden (0% host ratio).
NOLLAM_NO_HOST_PROFILES = {"nollam_file_v1"}


def _scaled_points(points: list[tuple[int, int]], scale: int) -> list[tuple[int, int]]:
    return [(x * scale, y * scale) for x, y in points]


def render_canonical_host_asset(output_path: Path) -> Path:
    """Render the deterministic recurring doodle host on a transparent canvas."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scale = 3
    width, height = 760, 1080
    image = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    ink = (20, 20, 20, 255)
    paper = (249, 247, 239, 255)
    pale = (237, 241, 239, 255)
    accent = (204, 210, 208, 255)

    def line(points: list[tuple[int, int]], fill=ink, width_px: int = 8) -> None:
        draw.line(_scaled_points(points, scale), fill=fill, width=width_px * scale, joint="curve")

    def polygon(points: list[tuple[int, int]], fill, outline=ink, width_px: int = 8) -> None:
        pts = _scaled_points(points, scale)
        draw.polygon(pts, fill=fill)
        draw.line(pts + [pts[0]], fill=outline, width=width_px * scale, joint="curve")

    def ellipse(box: tuple[int, int, int, int], fill, outline=ink, width_px: int = 8) -> None:
        draw.ellipse(tuple(value * scale for value in box), fill=fill, outline=outline, width=width_px * scale)

    # Full white dopo body and both wide sleeves.
    polygon([(355, 445), (590, 438), (672, 580), (730, 1080), (235, 1080), (272, 620)], paper)
    polygon([(372, 492), (294, 472), (218, 512), (130, 478), (82, 535), (198, 626), (350, 650)], paper)
    polygon([(585, 490), (650, 525), (708, 710), (637, 738), (560, 610)], paper)
    # Pointing hand remains small; the clothed sleeve is always visible.
    ellipse((72, 500, 132, 558), pale, ink, 7)
    line([(88, 515), (20, 463), (77, 476)], width_px=8)
    line([(87, 538), (36, 550)], width_px=7)

    # Collar, chest, waist tie, and robe folds make the costume unambiguous.
    polygon([(390, 445), (475, 548), (425, 615), (346, 492)], pale, ink, 6)
    polygon([(560, 448), (475, 548), (523, 618), (610, 490)], accent, ink, 6)
    line([(475, 548), (475, 1040)], width_px=6)
    polygon([(409, 650), (544, 650), (557, 688), (399, 688)], pale, ink, 6)
    line([(445, 688), (420, 852), (456, 818)], width_px=7)
    line([(516, 688), (548, 846), (512, 816)], width_px=7)
    line([(320, 720), (292, 1040)], fill=(95, 95, 95, 255), width_px=4)
    line([(626, 732), (671, 1038)], fill=(95, 95, 95, 255), width_px=4)

    # Circular face with dot eyes and a restrained smile.
    ellipse((350, 214, 615, 484), paper, ink, 9)
    ellipse((418, 314, 434, 332), ink, ink, 1)
    ellipse((526, 314, 542, 332), ink, ink, 1)
    line([(453, 389), (476, 400), (500, 389)], width_px=5)
    line([(365, 408), (337, 430)], width_px=6)
    line([(601, 408), (623, 432)], width_px=6)

    # Canonical black gat: broad brim plus a fixed crown silhouette.
    ellipse((286, 174, 682, 292), ink, ink, 6)
    polygon([(390, 180), (414, 65), (566, 68), (600, 205)], ink, ink, 6)
    line([(410, 178), (586, 194)], fill=(65, 65, 65, 255), width_px=5)
    line([(366, 268), (338, 448)], width_px=5)
    line([(603, 267), (625, 448)], width_px=5)

    image = image.resize((width, height), Image.Resampling.LANCZOS)
    image.save(output_path, format="PNG", optimize=True)
    return output_path


def composite_canonical_host(
    base_image_path: Path,
    overlay_path: Path,
    output_path: Path,
    *,
    profile_id: str = "doodle_seonbi_v1",
    width_ratio: float = 0.38,
    margin_right: int = 24,
) -> dict[str, Any]:
    """Composite the exact same canonical host at the right edge of a generated base.

    Raises ValueError if profile_id is in NOLLAM_NO_HOST_PROFILES (host overlay = 0%).
    """
    if profile_id in NOLLAM_NO_HOST_PROFILES:
        raise ValueError(
            f"Host overlay is forbidden for profile '{profile_id}'. "
            f"Nollam cinematic documentary uses 0% host avatar ratio."
        )
    base_image_path = Path(base_image_path)
    overlay_path = Path(overlay_path)
    output_path = Path(output_path)
    with Image.open(base_image_path) as source:
        base = source.convert("RGBA")
    with Image.open(overlay_path) as source_overlay:
        overlay = source_overlay.convert("RGBA")
    target_width = max(1, round(base.width * width_ratio))
    target_height = round(overlay.height * target_width / overlay.width)
    if target_height > base.height:
        target_height = base.height
        target_width = round(overlay.width * target_height / overlay.height)
    overlay = overlay.resize((target_width, target_height), Image.Resampling.LANCZOS)
    x = max(0, base.width - target_width - margin_right)
    y = max(0, base.height - target_height)
    base.alpha_composite(overlay, (x, y))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(output_path, format="JPEG", quality=95, subsampling=0)
    return {
        "type": "canonical_host_overlay",
        "overlay_sha256": compute_file_sha256(overlay_path),
        "output_sha256": compute_file_sha256(output_path),
        "anchor": "right_bottom",
        "width_ratio": width_ratio,
        "costume": CANONICAL_HOST_COSTUME,
    }
