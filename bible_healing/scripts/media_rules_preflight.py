from pathlib import Path
import json, sys
R=Path(r"C:\Users\amd\module"); J=R/"bible_healing/runs/ep01_anxious_night/hermes_jobs/full"; L=json.loads((R/"bible_healing/config/media_rules_lock.json").read_text(encoding='utf-8')); errors=[]
vm=json.loads((J/"voice_map.json").read_text(encoding='utf-8-sig'))
if vm['speakers']['scripture']['voice']!=L['voice']['scripture']['voice'] or float(vm['speakers']['scripture']['speed'])!=L['voice']['scripture']['speed']: errors.append('stale_voice_map_scripture_not_M4_0.72')
ro=json.loads((J/"render-options.json").read_text(encoding='utf-8-sig'))
if ro.get('engineVoice') in ('F3','M5') or float(ro.get('speechSpeed',0))!=0.72: errors.append('stale_render_options_voice_or_speed')
bg=R/L['background']['directory']; samples=sorted(bg.glob('*.mp4'))
if len(samples)!=L['background']['required_count']: errors.append(f'background_count:{len(samples)}')
if not Path(L['storage']['final_root']).exists(): errors.append('missing_D_final_root')
if not (J/'authoritative_audio_rebuild/full-authoritative-audio.wav').exists(): errors.append('missing_authoritative_audio')
if not (J/'authoritative_audio_rebuild/voice_provenance.json').exists(): errors.append('missing_voice_provenance_rebuild_required')
result={'ok':not errors,'errors':errors,'canonical':str(R/'bible_healing/config/media_rules_lock.json'),'background_count':len(samples)}
print(json.dumps(result,ensure_ascii=False,indent=2)); sys.exit(0 if not errors else 1)
