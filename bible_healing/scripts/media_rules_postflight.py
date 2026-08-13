from pathlib import Path
import json, subprocess, sys, re
L=json.loads(Path(r"C:\Users\amd\module\bible_healing\config\media_rules_lock.json").read_text(encoding='utf-8')); out=Path(sys.argv[1]) if len(sys.argv)>1 else Path(r"D:\bible_healing_ep01\final\deploy-ep01-authoritative-audio-aligned.mp4"); errors=[]
fp=Path(r"C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe"); p=json.loads(subprocess.check_output([str(fp),'-v','error','-show_entries','format=duration:stream=codec_type,codec_name','-of','json',str(out)],text=True)); dur=float(p['format']['duration']); types={s['codec_type'] for s in p['streams']}
if types!={'video','audio'}: errors.append('missing_audio_or_video_stream')
ass=Path(r"C:\Users\amd\module\bible_healing\runs\ep01_anxious_night\hermes_jobs\full\subtitles-full-audio-aligned.ass"); lines=[x for x in ass.read_text(encoding='utf-8-sig').splitlines() if x.startswith('Dialogue:')]; last=lines[-1].split(',')[2] if lines else ''
def sec(x):
 h,m,s=x.split(':'); return int(h)*3600+int(m)*60+float(s)
if not last or abs(sec(last)-dur)>L['release_gates']['duration_delta_seconds']: errors.append(f'subtitle_duration_delta:{last}/{dur:.3f}')
result={'ok':not errors,'output':str(out),'duration':dur,'subtitle_last':last,'errors':errors}; print(json.dumps(result,ensure_ascii=False,indent=2)); sys.exit(0 if not errors else 1)
