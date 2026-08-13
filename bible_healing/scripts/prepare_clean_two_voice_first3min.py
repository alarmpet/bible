from pathlib import Path
import json,re

ROOT=Path(r"C:\Users\amd\module")
SRC=ROOT/"bible_healing/runs/ep01_anxious_night/hermes_jobs/actual_first3min_locked_M4"
DST=ROOT/"bible_healing/runs/ep01_anxious_night/hermes_jobs/actual_first3min_clean_two_voice"
DST.mkdir(parents=True,exist_ok=True)

def clean(t):
    t=re.sub(r"\([^)]*\)"," ",t or "")
    t=re.sub(r"(?i)\bselah\b"," ",t)
    t=t.replace("!",".").replace("❗",".")
    return re.sub(r"\s+"," ",t).strip()

scenes=json.loads((SRC/"scenes.json").read_text(encoding="utf-8"))
for s in scenes:
    for seg in s.get("segments",[]):
        seg["text_source"]=seg.get("text","")
        seg["text"]=clean(seg.get("text",""))
    s["narration_source"]=s.get("narration","")
    s["narration"]=clean(s.get("narration", ""))
(DST/"scenes.json").write_text(json.dumps(scenes,ensure_ascii=False,indent=2),encoding="utf-8")
vm=json.loads((SRC/"voice_map.json").read_text(encoding="utf-8"))
vm["speakers"]["narrator"]["voice"]="F5"
vm["speakers"]["scripture"].update({"voice":"M4","speed":0.72,"total_step":12,"silence_duration":0.65})
vm["notes"]="CLEAN TWO VOICE LOCK: female narrator + male scripture; titles/Selah/metadata removed before TTS"
(DST/"voice_map.json").write_text(json.dumps(vm,ensure_ascii=False,indent=2),encoding="utf-8")
print({"job":str(DST),"scenes":len(scenes),"speakers":["narrator_female","scripture_male"]})
