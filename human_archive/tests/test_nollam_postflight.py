from human_archive.scripts.lib.nollam_visual_gate import compile_overlay_events
from human_archive.scripts.nollam_file_postflight import (
    validate_render_contract,
    validate_duration,
    validate_full_postflight,
)


def test_overlay_manifest_separates_base_image_text_from_labels():
    manifest = compile_overlay_events([{"sentence_id": "s1", "label": "확인", "text": "공식 발표"}])
    assert manifest["base_image_text_policy"] == "no_glyph"
    assert manifest["events"][0]["label"] == "확인"


def test_postflight_requires_nollam_longform_contract():
    result = validate_render_contract({"width": 1920, "height": 1080, "fps": 25, "format_id": "nollam_file_long", "voice_lock_id": "M2_WARM"})
    assert result["ok"] is True


def test_postflight_validates_20m_duration_bounds():
    # Exactly target 1200s (20 min) -> pass
    res_target = validate_duration(1200.0)
    assert res_target["ok"] is True
    assert res_target["deviation_pct"] == 0.0

    # 14 min (840s) -> minimum bound pass
    res_min = validate_duration(840.0)
    assert res_min["ok"] is True

    # 26 min (1560s) -> maximum bound pass
    res_max = validate_duration(1560.0)
    assert res_max["ok"] is True

    # 10 min (600s) -> below minimum fail
    res_too_short = validate_duration(600.0)
    assert res_too_short["ok"] is False
    assert any("below minimum" in f for f in res_too_short["failures"])

    # 30 min (1800s) -> exceeds maximum fail
    res_too_long = validate_duration(1800.0)
    assert res_too_long["ok"] is False
    assert any("exceeds maximum" in f for f in res_too_long["failures"])


def test_postflight_accepts_quick_3m_duration_bounds_via_override():
    """2026-09-16 finding: validate_duration() was hardcoded to
    trend_explainer_20m's 840-1560s bounds only, so it rejected a real,
    correctly rendered quick_3m episode's ~190s duration outright. Passing
    the delivery profile's own bounds (config/delivery_profiles.yaml's
    quick_3m: 170/190/180) must accept it."""
    res = validate_duration(189.7, min_sec=170.0, max_sec=190.0, target_sec=180.0)
    assert res["ok"] is True

    # the historical default (no override) must still reject a quick_3m-length
    # duration, so a caller that forgets to pass the profile's bounds fails
    # loudly instead of silently validating against the wrong target
    res_default = validate_duration(189.7)
    assert res_default["ok"] is False


def test_full_postflight_integration():
    render_valid = {"width": 1920, "height": 1080, "fps": 25, "format_id": "nollam_file_long", "voice_lock_id": "M2_WARM"}
    res_pass = validate_full_postflight(render_valid, 1185.0)
    assert res_pass["ok"] is True

    render_invalid = {"width": 1280, "height": 720, "fps": 30, "format_id": "short", "voice_lock_id": "OTHER"}
    res_fail = validate_full_postflight(render_invalid, 500.0)
    assert res_fail["ok"] is False
    assert len(res_fail["failures"]) >= 4
