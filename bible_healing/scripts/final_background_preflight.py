from pathlib import Path
import json,sys,subprocess
ROOT=Path(__file__).resolve().parents[2]
POL=json.loads((ROOT/'bible_healing/config/final_render_policy.json').read_text(encoding='utf-8'))
BG=ROOT/POL['required_background']['directory']; FP=Path(r'C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe'); files=list(BG.glob('*.mp4')); bad=[]
if not files: bad.append('no ambient mp4 files found')
for p in files:
 try: d=float(subprocess.check_output([str(FP),'-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(p)],text=True).strip())
 except Exception: bad.append(f'probe_failed:{p.name}'); continue
 if abs(d-60)>0.2: bad.append(f'not_60_seconds:{p.name}:{d}')
print(json.dumps({'directory':str(BG),'files':len(files),'errors':bad},ensure_ascii=False)); sys.exit(1 if bad else 0)
