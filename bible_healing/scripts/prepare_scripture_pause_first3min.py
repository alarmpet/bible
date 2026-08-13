from pathlib import Path
import json,re

ROOT=Path(r"C:\Users\amd\module")
SRC=ROOT/"bible_healing/runs/ep01_anxious_night/hermes_jobs/actual_first3min_clean_two_voice"
DST=ROOT/"bible_healing/runs/ep01_anxious_night/hermes_jobs/actual_first3min_pause_split"
DST.mkdir(parents=True,exist_ok=True)
ENDINGS=r"(?:할지어다|하리니|이로다|이니라|하시니라|하였느니라|되리라|있으리라|없느니라|아멘)"
def clean(t):
    t=re.sub(r"\([^)]*\)"," ",t or "")
    t=re.sub(r"(?i)\bselah\b"," ",t)
    return re.sub(r"\s+"," ",t.replace("!",".").replace("❗",".")).strip()
def split_text(t):
    t=clean(t)
    # Insert a real segment boundary after biblical declarative endings.
    t=re.sub(rf"({ENDINGS})(?=\s|$)",r"\1|",t)
    t=re.sub(r"([.!?。！？])\s*",r"\1|",t)
    return [x.strip(" |") for x in t.split("|") if x.strip(" |")]
scenes=json.loads((SRC/"scenes.json").read_text(encoding="utf-8"))
for s in scenes:
    new=[]
    for seg in s.get("segments",[]):
        if seg.get("speaker")=="scripture":
            for j,piece in enumerate(split_text(seg.get("text","")),1):
                new.append({**seg,"seg_id":f"{seg.get('seg_id','seg')}_pause{j:02d}","text":piece,"text_source":seg.get("text_source",seg.get("text",""))})
        else:
            seg["text"]=clean(seg.get("text","")); new.append(seg)
    s["segments"]=new
    s["narration"]=" ".join(x.get("text","") for x in new)
(DST/"scenes.json").write_text(json.dumps(scenes,ensure_ascii=False,indent=2),encoding="utf-8")
vm=json.loads((SRC/"voice_map.json").read_text(encoding="utf-8")); vm["speakers"]["scripture"].update({"voice":"M4","speed":0.72,"total_step":12,"silence_duration":0.55}); vm["notes"]="PAUSE SPLIT LOCK: two voices only; scripture endings segmented before TTS"
(DST/"voice_map.json").write_text(json.dumps(vm,ensure_ascii=False,indent=2),encoding="utf-8")
print({"job":str(DST),"scripture_segments":sum(len([x for x in s.get('segments',[]) if x.get('speaker')=='scripture']) for s in scenes)})
