from __future__ import annotations
import json
from pathlib import Path
from PIL import Image
from flow_automation.native_host.semantic_review import build_contact_sheet, record_review, review_status, evaluate_semantic_policy

def manifest(tmp_path: Path) -> Path:
    assets=[]
    for i in range(1,3):
        path=tmp_path/f'SHOT_00{i}.png'; Image.new('RGB',(1920,1080),(i*30,50,80)).save(path); assets.append({'shot_id':f'SHOT_00{i}','approved_path':str(path),'attempt':1,'prompt':f'prompt {i}'})
    p=tmp_path/'approved.json'; p.write_text(json.dumps({'assets':assets}),encoding='utf-8'); return p

def test_contact_sheet_labels_every_shot_in_manifest_order(tmp_path: Path):
    report=build_contact_sheet(manifest(tmp_path),tmp_path/'sheet.jpg'); assert report['shot_ids']==['SHOT_001','SHOT_002']; assert Path(report['output_path']).exists()

def test_asset_change_invalidates_prior_review(tmp_path: Path):
    p=manifest(tmp_path); review=record_review(p,'tester','approved',[]); assert review_status(p,review)=='APPROVED'; data=json.loads(p.read_text()); data['assets'][1]['attempt']=2; p.write_text(json.dumps(data)); assert review_status(p,review)=='REVIEW_REQUIRED'

def test_unsupported_semantic_scorer_pauses():
    assert evaluate_semantic_policy({'shots':[]},{'assets':[]},'auto')=={'status':'PAUSED','code':'SEMANTIC_SCORER_UNAVAILABLE'}
