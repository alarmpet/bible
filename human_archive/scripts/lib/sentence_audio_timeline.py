from __future__ import annotations

from typing import Any

def build_sentence_rows(
    sentences: list[dict[str, Any]],
    durations: dict[str, float],
    gap_sec: float = 0.35,
    wav_sha256_by_id: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    if not 0.35 <= float(gap_sec) <= 0.50:
        raise ValueError("inter-sentence room-tone gap must be between 0.35 and 0.50 seconds")
    rows=[]; cursor=0.0
    ordered=sorted(sentences,key=lambda x:(int(x["order"]),str(x["sentence_id"])))
    for i,s in enumerate(ordered):
        sid=str(s["sentence_id"]); duration=round(float(durations[sid]),3)
        start=round(cursor,3); end=round(start+duration,3)
        row = {"sentence_id":sid,"order":int(s["order"]),"chapter":s.get("chapter",1),"beat":str(s.get("beat","body"),),"tts_text":str(s["tts_text"]),"start_sec":start,"end_sec":end,"duration_sec":duration,"audio_file":f"{sid}.wav","provenance":{}}
        if wav_sha256_by_id is not None:
            row["wav_sha256"] = str(wav_sha256_by_id[sid])
        rows.append(row)
        cursor=end+(gap_sec if i+1<len(ordered) else 0.0)
    return rows

def validate_sentence_timeline(script: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    errors=[]; expected=[str(s["sentence_id"]) for s in sorted(script.get("sentences",[]),key=lambda x:int(x["order"]))]
    actual=[str(s.get("sentence_id")) for s in manifest.get("sentences",[])]
    for sid in expected:
        if sid not in actual: errors.append(f"{sid} missing")
    if actual != expected: errors.append("sentence order mismatch")
    prev_end=-1.0
    for row in manifest.get("sentences",[]):
        start=float(row.get("start_sec",0)); end=float(row.get("end_sec",0)); dur=float(row.get("duration_sec",0))
        if dur<=0 or end<=start: errors.append(f"{row.get('sentence_id')} invalid duration")
        if start < prev_end-0.02: errors.append(f"{row.get('sentence_id')} overlaps previous sentence")
        if abs((end-start)-dur)>0.02: errors.append(f"{row.get('sentence_id')} duration mismatch")
        prev_end=end
    return errors
