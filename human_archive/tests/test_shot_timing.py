from lib.shot_timing import ShotTimingProfile, plan_shot_timing
P=ShotTimingProfile(9,10.5,12,15,2)
def test_planner_combines_short_sentences_but_not_past_max():
 s={"episode_id":"HA002","sentences":[{"sentence_id":"S1","order":1,"chapter":1,"beat":"body","tts_text":"하나"},{"sentence_id":"S2","order":2,"chapter":1,"beat":"body","tts_text":"둘"},{"sentence_id":"S3","order":3,"chapter":1,"beat":"body","tts_text":"셋"}]}
 a={"sentences":[{"sentence_id":"S1","start_sec":0,"end_sec":4},{"sentence_id":"S2","start_sec":4.35,"end_sec":9.35},{"sentence_id":"S3","start_sec":9.7,"end_sec":19.7}]}
 r=plan_shot_timing(s,a,{},P); assert [x["sentence_spans"][0]["sentence_id"] for x in r["shots"]]==["S1","S3"]


def test_planner_uses_explicit_versioned_shot_id_prefix():
 s={"episode_id":"HA002","sentences":[{"sentence_id":"S1","order":1,"chapter":1,"beat":"body","tts_text":"하나"}]}
 a={"sentences":[{"sentence_id":"S1","start_sec":0,"end_sec":4}]}
 r=plan_shot_timing(s,a,{},P,shot_id_prefix="ha002_v6_shot")
 assert r["shots"][0]["shot_id"]=="ha002_v6_shot_001"


def test_preferred_beat_change_does_not_force_an_under_minimum_shot():
 s={"episode_id":"HA002","sentences":[
  {"sentence_id":"S1","order":1,"chapter":1,"beat":"body","tts_text":"하나"},
  {"sentence_id":"S2","order":2,"chapter":1,"beat":"insight","tts_text":"둘"},
 ]}
 a={"sentences":[
  {"sentence_id":"S1","start_sec":0,"end_sec":4},
  {"sentence_id":"S2","start_sec":4.35,"end_sec":9.35},
 ]}
 r=plan_shot_timing(s,a,{},P)
 assert len(r["shots"])==1
 assert r["shots"][0]["duration_sec"]==9.35


def test_chapter_change_remains_a_hard_boundary():
 s={"episode_id":"HA002","sentences":[
  {"sentence_id":"S1","order":1,"chapter":1,"beat":"body","tts_text":"하나"},
  {"sentence_id":"S2","order":2,"chapter":2,"beat":"body","tts_text":"둘"},
 ]}
 a={"sentences":[
  {"sentence_id":"S1","start_sec":0,"end_sec":4},
  {"sentence_id":"S2","start_sec":4.35,"end_sec":9.35},
 ]}
 r=plan_shot_timing(s,a,{},P)
 assert len(r["shots"])==2
