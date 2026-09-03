from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from PIL import Image, ImageDraw

def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _manifest(value: Path | Mapping[str, Any]) -> tuple[dict[str, Any], Path | None]:
    if isinstance(value, Path): return json.loads(value.read_text(encoding='utf-8')), value
    return dict(value), None

def build_contact_sheet(manifest_path: Path, output_path: Path) -> dict[str, Any]:
    manifest, _ = _manifest(Path(manifest_path))
    assets = manifest.get('assets', [])
    if not assets: raise ValueError('approved manifest must contain assets')
    thumb_w, thumb_h, label_h = 360, 240, 58
    sheet = Image.new('RGB', (thumb_w * 4, (thumb_h + label_h) * ((len(assets) + 3) // 4)), 'white')
    draw = ImageDraw.Draw(sheet)
    ids = []
    for index, asset in enumerate(assets):
        ids.append(str(asset['shot_id']))
        with Image.open(asset['approved_path']) as source:
            image = source.convert('RGB'); image.thumbnail((thumb_w, thumb_h))
            tile = Image.new('RGB', (thumb_w, thumb_h), '#dddddd'); tile.paste(image, ((thumb_w-image.width)//2, (thumb_h-image.height)//2))
        x, y = (index % 4) * thumb_w, (index // 4) * (thumb_h + label_h)
        sheet.paste(tile, (x, y)); draw.text((x + 6, y + thumb_h + 5), f"{asset['shot_id']}  attempt={asset.get('attempt', 0)}\n{str(asset.get('prompt', ''))[:48]}", fill='black')
    output_path.parent.mkdir(parents=True, exist_ok=True); sheet.save(output_path, format='JPEG', quality=92)
    return {'status': 'PASS', 'shot_ids': ids, 'output_path': str(output_path)}

def evaluate_semantic_policy(job: Mapping[str, Any], manifest: Mapping[str, Any], mode: str) -> dict[str, Any]:
    if mode != 'manual_contact_sheet': return {'status': 'PAUSED', 'code': 'SEMANTIC_SCORER_UNAVAILABLE'}
    expected = [str(shot['shot_id']) for shot in job.get('shots', [])]
    actual = [str(asset['shot_id']) for asset in manifest.get('assets', [])]
    return {'status': 'PASS' if actual == expected else 'REVIEW_REQUIRED', 'code': None if actual == expected else 'INCOMPLETE_ASSET_SET'}

def record_review(manifest_path: Path, reviewer: str, decision: str, per_shot: list[Mapping[str, Any]]) -> dict[str, Any]:
    if decision not in {'approved', 'rejected'}: raise ValueError('decision must be approved or rejected')
    return {'schema_version': 1, 'approved_asset_manifest_sha256': _digest(Path(manifest_path)), 'decision': decision, 'reviewer': reviewer, 'shot_results': [dict(item) for item in per_shot], 'created_at': datetime.now(timezone.utc).isoformat()}

def review_status(manifest_path: Path, review: Mapping[str, Any]) -> str:
    return 'APPROVED' if review.get('approved_asset_manifest_sha256') == _digest(Path(manifest_path)) and review.get('decision') == 'approved' else 'REVIEW_REQUIRED'
