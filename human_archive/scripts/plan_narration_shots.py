from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path
import yaml
from lib.shot_timing import ShotTimingProfile,plan_shot_timing

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--script',type=Path,required=True); ap.add_argument('--audio',type=Path,required=True); ap.add_argument('--profile',default='narration_aligned_hybrid_v1'); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--claims',type=Path); ap.add_argument('--shot-id-prefix')
 a=ap.parse_args(); script=json.loads(a.script.read_text(encoding='utf-8')); audio=json.loads(a.audio.read_text(encoding='utf-8')); cfg=yaml.safe_load((audio.parents[2]/'config'/'visual_pacing_profiles.yaml').read_text(encoding='utf-8')) if False else yaml.safe_load((Path(__file__).parents[1]/'config'/'visual_pacing_profiles.yaml').read_text(encoding='utf-8'))[a.profile]
 p=ShotTimingProfile(cfg['min_shot_sec'],cfg['target_shot_sec'],cfg['max_shot_sec'],cfg['hard_max_shot_sec'],cfg['max_sentences_per_shot']); claims=json.loads(a.claims.read_text(encoding='utf-8')) if a.claims and a.claims.exists() else {}
 result=plan_shot_timing(script,audio,claims,p,shot_id_prefix=a.shot_id_prefix); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__': main()
