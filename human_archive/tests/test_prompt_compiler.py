from __future__ import annotations

from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from lib.prompt_compiler import compile_policy_safe_retry, compile_scene_request


def test_compiler_preserves_scene_order_and_negative_metadata():
    scene = {
        "scene_id": "scene-1", "subject_refs": ["char-jang"], "visual_beat": "기록 문서를 펼친다",
        "action": ["문서를 펼친다"], "place": "취선당 서고", "era": "조선 숙종대",
        "camera": "medium close-up", "composition": "focal anchor on document",
        "lighting": "candlelight", "style": "historical documentary", "must_not": ["modern objects"],
        "forbidden_implications": ["photographic evidence"], "subtitle_safe_area": "lower third clear",
    }
    request = compile_scene_request(scene, provider="flow")
    assert request["positive_prompt"].startswith("char-jang")
    assert "기록 문서를 펼친다" in request["positive_prompt"]
    assert "조선 숙종대" in request["positive_prompt"]
    assert request["negative"]["items"] == ["modern objects", "photographic evidence"]
    assert request["negative"]["mode"] == "prompt_exclusion"
    assert len(request["request_sha256"]) == 64


def test_compiler_rejects_missing_explicit_era():
    with pytest.raises(ValueError, match="era"):
        compile_scene_request({"scene_id": "scene-1", "visual_beat": "문서", "action": ["읽는다"], "place": "서고", "era": ""})


def _reconstruction_scene():
    return {
        "scene_id": "scene-safe",
        "visual_role": "historical_reconstruction",
        "host_mode": "absent",
        "historical_subjects": ["숙종", "대신"],
        "visual_beat": "숙종이 대신들과 명령을 논의한다",
        "action": ["숙종이 대신들과 명령을 논의한다"],
        "place": "royal council hall",
        "era_context": "1701 (조선 숙종 27년)",
        "overlay_text": ["1701년"],
        "must_not": [],
        "camera": "medium character action",
        "composition": "filled composition",
        "lighting": "soft flat candlelight",
        "style": "hand-drawn doodle",
    }


def test_reconstruction_prompt_has_no_host_digits_or_overlay_text():
    request = compile_scene_request(_reconstruction_scene())
    prompt = request["positive_prompt"].lower()
    assert "seonbi" not in prompt
    assert "1701" not in prompt
    assert not any(character.isdigit() for character in prompt)
    assert "1701년" not in prompt
    assert {"letters", "numerals", "captions", "signage"} <= set(request["negative"]["items"])
    assert request["overlay_text"] == ["1701년"]
    assert "all surfaces and papers remain completely blank" in request["submission_prompt"].lower()
    assert "speech balloons" in request["submission_prompt"].lower()
    assert "wall plaques" in request["submission_prompt"].lower()
    assert "hanging scrolls" in request["submission_prompt"].lower()
    assert not any(character.isdigit() for character in request["submission_prompt"])


def test_host_reference_is_rejected_for_non_host_role():
    scene = {**_reconstruction_scene(), "host_reference_assets": ["seonbi.png"]}
    with pytest.raises(ValueError, match="host reference"):
        compile_scene_request(scene)


def test_host_prompt_allows_canonical_reference_only_for_host_role():
    scene = {
        **_reconstruction_scene(),
        "visual_role": "host_explainer",
        "host_mode": "full",
        "host_reference_assets": ["canonical_seonbi.png"],
    }
    request = compile_scene_request(scene)
    assert request["host_reference_assets"] == ["canonical_seonbi.png"]
    assert "presenter absent from the generated base" in request["positive_prompt"].lower()
    assert "right side" in request["positive_prompt"].lower()
    assert "single-line limbs" not in request["positive_prompt"].lower()
    assert request["host_overlay"]["asset"] == "human_archive/assets/doodle_seonbi_v1.png"
    assert request["host_overlay"]["costume"] == "white dopo with full torso, sleeves, collar, and waist tie"


def test_host_base_prompt_cannot_generate_a_second_presenter_or_body_parts():
    scene = {
        **_reconstruction_scene(),
        "visual_role": "host_explainer",
        "host_mode": "full",
        "action": ["the presenter points toward a simple symbolic vignette"],
    }
    request = compile_scene_request(scene)
    prompt = request["submission_prompt"].lower()
    assert "presenter points" not in prompt
    assert "숙종" not in prompt
    assert "대신" not in prompt
    assert "object-only historical vignette" in prompt
    assert "no people" in prompt
    assert "no hands" in prompt
    assert "no human body parts" in prompt
    assert "single coherent vignette" in prompt
    assert {"additional person", "disembodied hand", "collage", "catalogue sheet"} <= set(
        request["negative"]["items"]
    )


def test_evidence_prompt_is_one_coherent_object_scene_without_catalogue_or_hands():
    scene = {
        **_reconstruction_scene(),
        "visual_role": "evidence_object",
        "host_mode": "absent",
        "action": ["historical figures take part in a restrained royal council debate"],
        "composition": "filled editorial doodle composition",
    }
    request = compile_scene_request(scene)
    prompt = request["submission_prompt"].lower()
    assert "royal court clothing and architecture" not in prompt
    assert "filled editorial" not in prompt
    assert "historical figures" not in prompt
    assert "debate" not in prompt
    assert "hands" not in prompt.replace("no hands", "")
    assert "single coherent object-focused scene" in prompt
    assert "no people" in prompt
    assert "no hands" in prompt
    assert "no human body parts" in prompt
    assert "no collage" in prompt
    assert "no catalogue" in prompt
    assert {"collage", "catalogue sheet", "costume display", "disembodied hand"} <= set(
        request["negative"]["items"]
    )


def _semantic_retry_scene(*, visual_mode: str = "historical_reconstruction"):
    return {
        "scene_id": "scene-semantic-001",
        "shot_id": "shot-semantic-001",
        "visual_mode": visual_mode,
        "semantic_anchor_ids": ["anchor-king", "anchor-case", "anchor-hall"],
        "required_semantic_anchor_ids": ["anchor-king", "anchor-case"],
        "semantic_anchors": ["King Sukjong", "sealed command case", "royal council hall"],
        "claim_ids": ["CLM-JH-001"],
        "actors": ["King Sukjong", "senior ministers"],
        "action": "King Sukjong advances the sealed command case across the council floor",
        "place": "royal council hall",
        "era": "Joseon period",
        "focal_subject": "King Sukjong",
        "camera": "documentary observational framing",
    }


def test_attempt_one_preserves_narrated_identity_when_retry_replaces_it_with_generic_workroom_text():
    # Mutation caught: replacing actors/action with the old generic palace workroom collapse.
    scene = _semantic_retry_scene()
    request = compile_policy_safe_retry(scene, 1, previous_request_sha256="OLD-HASH")
    prompt = request["submission_prompt"].lower()

    assert request["policy_retry_attempt"] == 1
    assert request["policy_retry_transform"] == "safe_rephrase"
    assert request["policy_retry_reason"] == "provider_policy_rejected"
    assert request["previous_request_sha256"] == "OLD-HASH"
    assert request["scene_id"] == scene["scene_id"]
    assert request["shot_id"] == scene["shot_id"]
    assert request["visual_mode"] == scene["visual_mode"]
    assert request["semantic_anchor_ids"] == scene["semantic_anchor_ids"]
    assert request["required_semantic_anchor_ids"] == scene["required_semantic_anchor_ids"]
    assert request["claim_ids"] == scene["claim_ids"]
    assert request["place"] == scene["place"]
    assert request["era"] == scene["era"]
    assert "king sukjong" in prompt
    assert "advances the sealed command case across the council floor" in prompt
    assert "calm" in prompt
    assert "non-graphic" in prompt
    assert "educational" in prompt
    assert "generic palace workroom" not in prompt


def test_attempt_two_uses_mode_compatible_abstraction_instead_of_generic_wooden_table():
    # Mutation caught: collapsing every mode to a generic wooden-table object scene.
    scene = _semantic_retry_scene(visual_mode="evidence_artifact")
    scene.update(
        {
            "semantic_anchors": ["sealed archive case", "excavation context", "evidence object"],
            "actors": [],
            "action": "the named sealed archive case rests in its real excavation context",
            "place": "royal archive excavation chamber",
        }
    )
    request = compile_policy_safe_retry(scene, 2, reason="visual_mismatch")
    prompt = request["submission_prompt"].lower()

    assert request["policy_retry_attempt"] == 2
    assert request["policy_retry_transform"] == "safe_abstraction"
    assert request["policy_retry_reason"] == "visual_mismatch"
    assert request["visual_mode"] == "evidence_artifact"
    assert request["semantic_anchor_ids"] == scene["semantic_anchor_ids"]
    assert request["required_semantic_anchor_ids"] == scene["required_semantic_anchor_ids"]
    assert request["claim_ids"] == scene["claim_ids"]
    assert request["place"] == scene["place"]
    assert request["era"] == scene["era"]
    assert "the same named evidence object in its real archive or excavation context" in prompt
    assert "sealed archive case" in prompt
    assert "royal archive excavation chamber" in prompt
    assert "generic wooden table" not in prompt


def test_attempt_three_is_rejected_before_any_third_retry_is_compiled():
    # Mutation caught: allowing attempt 3 or silently compiling another request.
    with pytest.raises(ValueError, match="maximum.*two"):
        compile_policy_safe_retry(_semantic_retry_scene(), 3)


def test_retry_hash_ignores_inherited_self_hash_and_keeps_only_explicit_lineage():
    # Mutation caught: hashing the copied scene while its inherited request_sha256 is still present.
    first_scene = {**_semantic_retry_scene(), "request_sha256": "INHERITED-HASH-A"}
    second_scene = {**_semantic_retry_scene(), "request_sha256": "INHERITED-HASH-B"}

    first = compile_policy_safe_retry(first_scene, 1, previous_request_sha256="LINEAGE-HASH")
    second = compile_policy_safe_retry(second_scene, 1, previous_request_sha256="LINEAGE-HASH")

    assert first["request_sha256"] == second["request_sha256"]
    assert first["previous_request_sha256"] == "LINEAGE-HASH"
    assert second["previous_request_sha256"] == "LINEAGE-HASH"
    assert "INHERITED-HASH-A" not in first.values()
    assert "INHERITED-HASH-B" not in second.values()


def test_named_palace_place_is_generalized_in_provider_prompt_to_avoid_signage():
    scene = {**_reconstruction_scene(), "place": "Chwiseondang palace quarters"}
    request = compile_scene_request(scene)
    assert "chwiseondang" not in request["submission_prompt"].lower()
    assert "late joseon palace quarters" in request["submission_prompt"].lower()
