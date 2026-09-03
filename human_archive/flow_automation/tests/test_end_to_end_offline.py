from __future__ import annotations
import json
from pathlib import Path
from PIL import Image
from flow_automation.native_host.job_store import append_event, replay_job
from flow_automation.native_host.semantic_review import build_contact_sheet

def make_job(tmp_path: Path) -> dict:
    shots=[]
    for i in range(1,3):
        shots.append({'shot_id':f'SHOT_00{i}','prompt':f'prompt {i}','prompt_sha256':'0'*64,'duration_sec':60,'expected_filename':f'SHOT_00{i}__00000000.png'})
    return {'job_id':'offline-j1','retry_limit':2,'shots':shots}

def event(job_id: str, shot_id: str, kind: str, attempt: int = 1) -> dict:
    return {'event_id':f'{shot_id}-{kind}-{attempt}','timestamp':'2026-09-03T00:00:00Z','job_id':job_id,'shot_id':shot_id,'attempt':attempt,'type':kind,'payload':{'approved_path':f'{shot_id}.png'} if kind == 'SHOT_ACCEPTED' else {}}

def test_two_shot_job_survives_restart_without_duplicate_submission(tmp_path: Path) -> None:
    job=make_job(tmp_path); events=tmp_path/'events.jsonl'
    append_event(events,event(job['job_id'],'SHOT_001','SHOT_SUBMITTED'))
    append_event(events,event(job['job_id'],'SHOT_001','SHOT_ACCEPTED'))
    restarted=replay_job(job,events)
    assert restarted.shots['SHOT_001'].status == 'ACCEPTED'
    append_event(events,event(job['job_id'],'SHOT_002','SHOT_SUBMITTED'))
    append_event(events,event(job['job_id'],'SHOT_002','SHOT_ACCEPTED'))
    final=replay_job(job,events)
    assert [shot_id for shot_id in final.shot_order if final.shots[shot_id].status == 'ACCEPTED'] == ['SHOT_001','SHOT_002']
    assert sum(1 for line in events.read_text().splitlines() if 'SHOT_SUBMITTED' in line) == 2

def test_offline_run_produces_contact_sheet_and_review_required_state(tmp_path: Path) -> None:
    job=make_job(tmp_path); assets=[]
    for i in range(1,3):
        image=tmp_path/f'SHOT_00{i}.png'; Image.new('RGB',(1920,1080),(i*20,40,60)).save(image)
        assets.append({'shot_id':f'SHOT_00{i}','approved_path':str(image),'attempt':1,'prompt':f'prompt {i}'})
    manifest=tmp_path/'approved_asset_manifest.json'; manifest.write_text(json.dumps({'assets':assets}),encoding='utf-8')
    sheet=build_contact_sheet(manifest,tmp_path/'contact-sheet.jpg')
    assert sheet['shot_ids'] == ['SHOT_001','SHOT_002']
    assert Path(sheet['output_path']).exists()
    assert 'review' not in {'state':'REVIEW_REQUIRED'}
