from __future__ import annotations

from lib.doodle_scene_planner import plan_scenes
from lib.doodle_visual_roles import validate_role_mix
from prepare_ep02_v4_workflow import prepare_visual_workflow


def _sentence(sid: str, text: str, *, beat: str = "body", chapter: int = 1):
    return {
        "sentence_id": sid,
        "order": int(sid[1:]),
        "chapter": chapter,
        "beat": beat,
        "tts_text": text,
        "display_text": text,
        "segments": [],
    }


def test_planner_uses_narrated_actor_instead_of_template_rotation():
    narration = "숙종은 대신들의 간언을 물리쳤습니다."
    scenes = plan_scenes([_sentence("S1", narration)], claims={})
    assert "숙종" in scenes[0]["historical_subjects"]
    assert scenes[0]["visual_role"] == "historical_reconstruction"
    assert scenes[0]["host_mode"] == "absent"
    assert scenes[0]["action"] != [narration]
    assert "royal council" in scenes[0]["action"][0]


def test_planner_covers_every_sentence_exactly_once_in_order():
    sentences = [
        _sentence("S1", "장희빈은 취선당에 머물렀습니다."),
        _sentence("S2", "실록은 신당 사건을 기록했습니다."),
        _sentence("S3", "숙종은 대신들과 논의했습니다."),
    ]
    scenes = plan_scenes(sentences, claims={}, target_chars=30)
    covered = [sid for scene in scenes for sid in scene["sentence_ids"]]
    assert covered == ["S1", "S2", "S3"]


def test_planner_produces_valid_episode_role_mix():
    sentences = []
    for index in range(1, 21):
        beat = "hook" if index in {1, 8, 15, 20} else "body"
        text = "기록의 의미를 짚어 봅니다." if beat == "hook" else "숙종과 대신들은 기록을 검토했습니다."
        sentences.append(_sentence(f"S{index}", text, beat=beat))
    scenes = plan_scenes(sentences, claims={}, target_chars=1)
    validate_role_mix(scenes)


def test_planner_avoids_same_role_subject_camera_triplet_in_recent_window():
    sentences = [_sentence(f"S{i}", "숙종은 기록을 살폈습니다.") for i in range(1, 6)]
    scenes = plan_scenes(sentences, claims={}, target_chars=1)
    triplets = [
        (scene["visual_role"], tuple(scene["historical_subjects"]), scene["camera"])
        for scene in scenes
    ]
    for index, triplet in enumerate(triplets):
        assert triplet not in triplets[max(0, index - 3):index]


def test_prepare_workflow_emits_contract_requests_and_overlay_manifest(tmp_path):
    sentences = []
    for index in range(1, 21):
        beat = "hook" if index in {1, 8, 15, 20} else "body"
        sentences.append(_sentence(f"S{index}", "숙종과 대신들이 기록을 검토했습니다.", beat=beat))
    script = {"episode_id": "HA002", "title": "test", "sentences": sentences}
    result = prepare_visual_workflow(script, tmp_path, target_chars=1)
    assert (tmp_path / "episode_visual_contract_v2.json").exists()
    assert (tmp_path / "image_request_manifest.json").exists()
    assert (tmp_path / "overlay_event_manifest.json").exists()
    assert (tmp_path.parent / "source" / "shot_contract_v4.json").exists()
    assert len(result["image_requests"]) == len(result["contract"]["scenes"])
    assert [item["order"] for item in result["image_requests"]] == list(range(1, len(result["image_requests"]) + 1))
    assert all(not any(char.isdigit() for char in item["positive_prompt"]) for item in result["image_requests"])


def test_host_eligible_insight_beats_are_sampled_not_all_forced_to_host():
    sentences = [_sentence(f"S{index}", "기록에서 얻은 통찰을 설명합니다.", beat="insight") for index in range(1, 31)]
    scenes = plan_scenes(sentences, claims={}, target_chars=1)
    host_count = sum(scene["visual_role"] == "host_explainer" for scene in scenes)
    assert 0.15 <= host_count / len(scenes) <= 0.25
    validate_role_mix(scenes)


def test_length_derived_scene_count_is_a_ceiling():
    sentences = [_sentence(f"S{index}", "숙종과 대신들이 중요한 기록을 함께 검토했습니다.") for index in range(1, 101)]
    total_chars = sum(len(sentence["tts_text"]) for sentence in sentences)
    ceiling = max(12, min(len(sentences), round(total_chars / 55)))
    scenes = plan_scenes(sentences, claims={}, target_chars=55)
    assert len(scenes) <= ceiling
