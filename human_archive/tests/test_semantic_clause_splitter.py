from __future__ import annotations

from lib.cinematic_editing_director import CinematicEditingDirector, split_sentence_by_semantic_clause


def test_long_sentence_splits_on_semantic_connective_without_text_loss() -> None:
    text = "차가운 북풍이 동굴 입구를 덮었고, 사냥꾼들은 불빛을 따라 안쪽으로 물러났습니다."

    clauses = split_sentence_by_semantic_clause(text, max_chars=35)

    assert clauses == [
        "차가운 북풍이 동굴 입구를 덮었고,",
        "사냥꾼들은 불빛을 따라 안쪽으로 물러났습니다.",
    ]
    assert " ".join(clauses) == text


def test_long_sentence_without_safe_boundary_is_not_midpoint_split() -> None:
    text = "초고해상도기록보관소의연속식별문자열은의미단위공백이나종결연결어미를포함하지않습니다"

    assert split_sentence_by_semantic_clause(text, max_chars=35) == [text]


def test_short_sentence_is_preserved() -> None:
    text = "빙하는 천천히 물러났습니다."

    assert split_sentence_by_semantic_clause(text, max_chars=35) == [text]


def test_tier_one_planner_uses_semantic_splitter_for_visual_cuts() -> None:
    hook = "이 영상은 사라진 종족의 마지막 선택을 추적합니다."
    split_text = "차가운 북풍이 동굴 입구를 덮었고, 사냥꾼들은 불빛을 따라 안쪽으로 물러났습니다."
    sentences = [hook, split_text] + [f"후속 문장 {index}의 사실을 설명합니다." for index in range(40)]

    shots = CinematicEditingDirector().split_script_by_variable_pacing(
        sentences,
        target_duration_sec=120.0,
    )

    split_shots = [shot["tts_text"] for shot in shots if shot["tts_text"] in split_sentence_by_semantic_clause(split_text)]
    assert split_shots == split_sentence_by_semantic_clause(split_text)
