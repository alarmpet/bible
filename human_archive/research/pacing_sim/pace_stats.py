import json, statistics, sys, collections
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
b = Path("D:/module/bible/human_archive/runs/ep02_jang_huibin/full-v6-001")
st = json.loads((b/"shot_timing_manifest.json").read_text(encoding="utf-8"))
sa = json.loads((b/"sentence_audio_manifest.json").read_text(encoding="utf-8"))
print("timing keys:", list(st.keys()))
print("profile_id:", st.get("profile_id"), "schema_version:", st.get("schema_version"))
shots = st["shots"]
print("shot keys:", list(shots[0].keys()))
print("n_shots:", len(shots), "total_end:", shots[-1]["end_sec"], "audio total:", sa.get("total_duration_sec"), "gap_sec:", sa.get("gap_sec"))
durs = [s["duration_sec"] for s in shots]
def summ(name, xs):
    if not xs: print(name, "EMPTY"); return
    xs2 = sorted(xs)
    print(f"{name}: n={len(xs)} mean={statistics.mean(xs):.2f} median={statistics.median(xs):.2f} min={min(xs):.2f} max={max(xs):.2f} p10={xs2[int(0.1*(len(xs)-1))]:.2f} p90={xs2[int(0.9*(len(xs)-1))]:.2f} sum={sum(xs):.1f}")
summ("ALL shots", durs)
bands = [(0,60),(60,120),(120,300),(300,1e9)]
for lo,hi in bands:
    xs = [s["duration_sec"] for s in shots if lo <= s["start_sec"] < hi]
    summ(f"shots start in [{lo},{hi if hi<1e8 else 'end'})", xs)
# histogram
hist = collections.Counter(int(d//3)*3 for d in durs)
print("hist (3s bins):", sorted(hist.items()))
print("boundary_reason:", collections.Counter(s["boundary_reason"] for s in shots))
print("sentences_per_shot:", collections.Counter(len({sp['sentence_id'] for sp in s['sentence_spans']}) for s in shots))
print("chapter dist:", collections.Counter(s["chapter"] for s in shots))
# chapter first-shot times
seen=set()
for s in shots:
    if s["chapter"] not in seen:
        seen.add(s["chapter"]); print(f"  chapter {s['chapter']} starts at shot {s['order']} t={s['start_sec']:.1f}")
# first 12 shots
print("first 12 shots:")
for s in shots[:12]:
    print(f"  {s['shot_id']} {s['start_sec']:.2f}-{s['end_sec']:.2f} dur={s['duration_sec']:.2f} reason={s['boundary_reason']} nsent={len({sp['sentence_id'] for sp in s['sentence_spans']})}")
# sentence durations
sd = [r["duration_sec"] for r in sa["sentences"]]
summ("sentence dur", sd)
sl = [len(r["tts_text"]) for r in sa["sentences"]]
summ("sentence chars", sl)
print("sentence dur hist (1s bins):", sorted(collections.Counter(int(d) for d in sd).items()))
print("sentences <=5s:", sum(1 for d in sd if d<=5), " <=4s:", sum(1 for d in sd if d<=4), " >8s:", sum(1 for d in sd if d>8))
print("first 60s sentences:")
for r in sa["sentences"]:
    if r["start_sec"] < 60: print(f"  {r['sentence_id']} {r['start_sec']:.2f}-{r['end_sec']:.2f} dur={r['duration_sec']:.2f} ch={r['chapter']} beat={r['beat']} chars={len(r['tts_text'])} prov={r['provenance'].get('provider')}")
print("beats:", collections.Counter(r["beat"] for r in sa["sentences"]))
print("chapters(sent):", collections.Counter(r["chapter"] for r in sa["sentences"]))
print("sec/char:", sum(sd)/sum(sl))
