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


def test_shot_end_sec_extends_through_the_inter_sentence_gap_to_the_next_shot():
 """2026-09-16 finding from a real quick_3m build: a shot's end_sec used to
 stop at its own last sentence's raw end_sec, leaving the real audio's
 inter-sentence room-tone gap (gap_sec, e.g. 0.35s) owned by neither shot.
 Motion clips render to exactly duration_sec, so 23 such un-owned gaps
 (8.05s total in that real build) never appeared in the video -- the
 concatenated motion track ran that much shorter than the master audio, and
 the final ffmpeg mux's -shortest silently truncated that much off the END
 of the episode. A shot's end_sec must extend all the way to the next
 shot's start_sec, closing the gap."""
 s={"episode_id":"HA002","sentences":[
  {"sentence_id":"S1","order":1,"chapter":1,"beat":"body","tts_text":"하나"},
  {"sentence_id":"S2","order":2,"chapter":2,"beat":"body","tts_text":"둘"},
 ]}
 a={"sentences":[
  {"sentence_id":"S1","start_sec":0,"end_sec":4},
  {"sentence_id":"S2","start_sec":4.35,"end_sec":9.35},
 ],"total_duration_sec":9.35}
 r=plan_shot_timing(s,a,{},P)
 assert len(r["shots"])==2
 assert r["shots"][0]["end_sec"]==4.35
 assert r["shots"][0]["duration_sec"]==4.35
 # the last shot extends to the audio's own measured total, in case of
 # trailing room tone after the final sentence too
 assert r["shots"][1]["end_sec"]==9.35


def test_last_shot_extends_to_measured_total_duration_past_its_own_last_sentence():
 s={"episode_id":"HA002","sentences":[
  {"sentence_id":"S1","order":1,"chapter":1,"beat":"body","tts_text":"하나"},
 ]}
 a={"sentences":[{"sentence_id":"S1","start_sec":0,"end_sec":4}],"total_duration_sec":4.5}
 r=plan_shot_timing(s,a,{},P)
 assert r["shots"][0]["end_sec"]==4.5
 assert r["shots"][0]["duration_sec"]==4.5


def test_end_sec_extension_is_a_noop_without_declared_total_duration():
 """Fixtures/callers that don't declare total_duration_sec (most existing
 tests) must keep the exact historical last-shot end_sec -- extension only
 ever grows toward a measured total, never invents one."""
 s={"episode_id":"HA002","sentences":[
  {"sentence_id":"S1","order":1,"chapter":1,"beat":"body","tts_text":"하나"},
 ]}
 a={"sentences":[{"sentence_id":"S1","start_sec":0,"end_sec":4}]}
 r=plan_shot_timing(s,a,{},P)
 assert r["shots"][0]["end_sec"]==4
 assert r["shots"][0]["duration_sec"]==4
