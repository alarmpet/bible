from pathlib import Path
from flow_automation.native_host.render_runner import RenderGateError, build_render_manifest, choose_output_path, validate_concat_uniqueness, validate_render_gate

def job(): return {'shots':[{'shot_id':'SHOT_001','duration_sec':60},{'shot_id':'SHOT_002','duration_sec':60}]}
def assets(tmp_path): return {'assets':[{'shot_id':'SHOT_001','approved_path':str(tmp_path/'1.png'),'sha256':'a'},{'shot_id':'SHOT_002','approved_path':str(tmp_path/'2.png'),'sha256':'b'}]}

def test_repeated_concat_is_rejected(tmp_path: Path):
    p=tmp_path/'video_concat.txt'; p.write_text("file 'SHOT_001.png'\nfile 'SHOT_008.png'\nfile 'SHOT_001.png'\nfile 'SHOT_008.png'\n")
    errors=validate_concat_uniqueness(p); assert any('SHOT_001' in e and 'repeated' in e for e in errors); assert any('SHOT_008' in e for e in errors)
def test_gate_rejects_missing_or_unreviewed_assets(tmp_path: Path):
    a=assets(tmp_path); a['assets'].pop(); assert 'MISSING_APPROVED_ASSET' in validate_render_gate(job(),a,{'decision':'approved'})
def test_verified_output_uses_new_filename(tmp_path: Path): assert choose_output_path(tmp_path).name.endswith('VERIFIED-v1.mp4')
def test_render_manifest_requires_exact_review(tmp_path: Path):
    try: build_render_manifest(job(),assets(tmp_path),{'decision':'rejected'})
    except RenderGateError as exc: assert 'REVIEW_REQUIRED' in str(exc)
    else: raise AssertionError('gate unexpectedly passed')
