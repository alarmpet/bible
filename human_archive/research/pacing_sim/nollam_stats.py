import json, statistics, sys, collections, re
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
b = Path("D:/module/bible/human_archive/runs/nollam_file/2026-09-01/nepal-tunnel-rescue/20260901-kr-nepal-tunnel-v3-run6")
sa = json.loads((b/"sentence_audio_manifest.json").read_text(encoding="utf-8"))
print("audio keys:", list(sa.keys()))
print("n_sent:", len(sa["sentences"]), "total:", sa.get("total_duration_sec"), "gap:", sa.get("gap_sec"))
sd=[r["duration_sec"] for r in sa["sentences"]]
def summ(name, xs):
    if not xs: print(name,"EMPTY"); return
    xs2=sorted(xs); print(f"{name}: n={len(xs)} mean={statistics.mean(xs):.2f} median={statistics.median(xs):.2f} min={min(xs):.2f} max={max(xs):.2f} p10={xs2[int(0.1*(len(xs)-1))]:.2f} p90={xs2[int(0.9*(len(xs)-1))]:.2f} sum={sum(xs):.1f}")
summ("sentence dur", sd)
print("prov:", collections.Counter(r.get("provenance",{}).get("provider") for r in sa["sentences"]))
al = json.loads((b/"sentence_visual_alignment_v2.json").read_text(encoding="utf-8"))
print("alignment keys:", list(al.keys()))
for k,v in al.items():
    if isinstance(v,list): print(" list", k, len(v), "first keys:", list(v[0].keys()) if v and isinstance(v[0],dict) else v[:2])
    elif isinstance(v,dict): print(" dict", k, list(v.keys())[:15])
    else: print(" ", k, "=", str(v)[:120])
ff = (b/"visual_timeline_v3.ffconcat").read_text(encoding="utf-8")
print("---- ffconcat head ----"); print(ff[:1200])
durs=[float(x) for x in re.findall(r"duration\s+([0-9.]+)", ff)]
files=re.findall(r"file\s+'?([^'\n]+)'?", ff)
print("n_entries:", len(durs), "n_files:", len(files), "unique_files:", len(set(files)), "sum:", sum(durs))
summ("visual segment dur", durs)
# by time band
t=0.0; bands=[(0,60),(60,120),(120,300),(300,1e9)]; segs=[]
for d in durs: segs.append((t,d)); t+=d
for lo,hi in bands:
    summ(f"segments start in [{lo},{hi if hi<1e8 else 'end'})", [d for (s,d) in segs if lo<=s<hi])
