from pathlib import Path
import json, shutil

ROOT=Path(r"C:\Users\amd\module")
SRC=ROOT/"bible_healing/runs/ep01_anxious_night/hermes_jobs/full"
DST=ROOT/"bible_healing/runs/ep01_anxious_night/hermes_jobs/actual_first3min_locked_M4"
DST.mkdir(parents=True,exist_ok=True)
scenes=json.loads((SRC/"scenes.json").read_text(encoding="utf-8"))[:12]
(DST/"scenes.json").write_text(json.dumps(scenes,ensure_ascii=False,indent=2),encoding="utf-8")
draft={"scenes":[{"order":i+1,"scene_id":s.get("scene_id",f"scene_{i+1}"),"narration":s.get("narration","")} for i,s in enumerate(scenes)]}
(DST/"draft.json").write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding="utf-8")
vm=json.loads((SRC/"voice_map.json").read_text(encoding="utf-8"))
vm["speakers"]["scripture"].update({"voice":"M4","speed":0.72,"total_step":24,"silence_duration":0.65,"audio_filter":"pitch_shift=-8%"})
vm["notes"]="LOCKED actual first 3 min: M4 speed 0.72 step 24 silence 0.65, post pitch -8%"
(DST/"voice_map.json").write_text(json.dumps(vm,ensure_ascii=False,indent=2),encoding="utf-8")
print({"job":str(DST),"scenes":len(scenes),"voice":"M4","speed":0.72,"pitch":"-8%"})
