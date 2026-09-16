import json
import lib.prompt_lint as prompt_lint
from lib.aligned_prompt_compiler import compile_aligned_prompt
from validate_image_requests import validate


def _fake_groq_screen_outcome(ok=True, text=""):
    class _FakeOutcome:
        def __init__(self):
            self.ok = ok
            self.text = text
            self.detail = "" if ok else "simulated failure"
    return _FakeOutcome()


def test_groq_text_screen_is_opt_in_and_off_by_default(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        prompt_lint, "screen_prompt_text_policy_with_groq",
        lambda prompt, **kw: calls.append(prompt) or _fake_groq_screen_outcome(
            text="## VERDICT\nFLAGGED\n\n## REASON\nx"),
    )
    requests = [{
        "shot_id": "S001", "visual_mode": "historical_reconstruction",
        "semantic_anchors": ["a", "b"], "submission_prompt": "clean",
        "positive_prompt": "a stone tablet with an inscription",
    }]
    (tmp_path / "flow_image_prompts.json").write_text(json.dumps({"requests": requests}), encoding="utf-8")

    errors_default = validate(tmp_path)
    assert calls == []
    assert not any("groq" in e for e in errors_default)

    errors_with_groq = validate(tmp_path, include_groq_text_screen=True)
    assert len(calls) == 1
    assert any("groq flagged implied on-image text" in e for e in errors_with_groq)


def test_groq_text_screen_malformed_response_is_flagged_not_silently_clean(tmp_path, monkeypatch):
    """2026-09-16 pattern reused here: an unparseable Groq answer must never
    be treated as a pass."""
    monkeypatch.setattr(
        prompt_lint, "screen_prompt_text_policy_with_groq",
        lambda prompt, **kw: _fake_groq_screen_outcome(text="not in the expected format"),
    )
    requests = [{
        "shot_id": "S001", "visual_mode": "historical_reconstruction",
        "semantic_anchors": ["a", "b"], "submission_prompt": "clean",
        "positive_prompt": "a quiet courtyard",
    }]
    (tmp_path / "flow_image_prompts.json").write_text(json.dumps({"requests": requests}), encoding="utf-8")

    errors = validate(tmp_path, include_groq_text_screen=True)
    assert any("malformed" in e for e in errors)


def test_prompt_has_required_anchor_and_no_forced_year():
 p=compile_aligned_prompt({'shot_id':'S','visual_mode':'place_establishing','semantic_anchors':['서고'],'focal_subject':'서고','action':'사람들이 이동','place':'서고','era':'조선','camera':'wide'})
 assert p['semantic_anchors']==['서고']; assert '1701' not in p['submission_prompt']

def test_preflight_rejects_production_placeholder_brief(tmp_path):
 requests=[]
 for i in range(101):
  requests.append({'shot_id':f'S{i:03d}','visual_mode':'host_chapter_hinge' if i in range(0,100,10) else 'historical_reconstruction','semantic_anchors':['palace','official'],'submission_prompt':'narration-specific subject; depict the narrated action directly'})
 (tmp_path/'flow_image_prompts.json').write_text(json.dumps({'requests':requests}),encoding='utf-8')
 errors=validate(tmp_path)
 assert any('placeholder' in error for error in errors)

def test_quick_3m_nollam_build_is_not_rejected_for_shot_count_or_host_ratio(tmp_path):
    """2026-09-16 finding: this validator's shot-count (95-120) and host-ratio
    (0.08-0.12) checks are hardcoded for the nominal 1200s
    trend_explainer_20m/doodle host convention -- a real 24-shot quick_3m
    nollam_file_v1 build (host_ratio 0.0) was rejected outright on both axes.
    A contract declaring channel_profile nollam_file_v1 and a shorter
    target_duration_sec must scale/relax both checks instead."""
    import os

    requests = [
        {
            "shot_id": f"S{i:03d}",
            "visual_mode": "historical_reconstruction",
            "semantic_anchors": ["courtyard", "samurai"],
            "submission_prompt": "one concrete courtyard scene",
        }
        for i in range(24)
    ]
    (tmp_path / "flow_image_prompts.json").write_text(
        json.dumps({"requests": requests}), encoding="utf-8"
    )
    source_dir = tmp_path / "source"
    os.makedirs(source_dir, exist_ok=True)
    (source_dir / "episode_contract.json").write_text(
        json.dumps({"channel_profile": "nollam_file_v1", "target_duration_sec": 180}),
        encoding="utf-8",
    )

    errors = validate(tmp_path)
    assert errors == []


def test_preflight_rejects_hangul_text_anchors_and_generic_fallback(tmp_path):
 requests=[]
 for i in range(101):
  requests.append({
   'shot_id':f'S{i:03d}',
   'visual_mode':'host_chapter_hinge' if i in range(0,100,10) else 'historical_reconstruction',
   'semantic_anchors':['숙종의','거부는','처분'] if i==12 else ['palace gate','kneeling ministers','sealed command case'],
   'submission_prompt':'period-dressed palace figures perform the single concrete action described by the narration' if i==13 else 'one concrete palace scene',
  })
 (tmp_path/'flow_image_prompts.json').write_text(json.dumps({'requests':requests}),encoding='utf-8')
 errors=validate(tmp_path)
 assert any('hangul semantic anchor' in error for error in errors)
 assert any('placeholder' in error for error in errors)
