from __future__ import annotations

from lib.prompt_lint import lint_image_request


def test_lint_rejects_digits_and_generated_label_language():
    errors = lint_image_request({
        "visual_role": "historical_reconstruction",
        "positive_prompt": "A palace sign written with the date 1701",
        "host_reference_assets": [],
        "overlay_text": [],
    })
    assert any("digit" in error for error in errors)
    assert any("label" in error for error in errors)


def test_lint_rejects_host_reference_outside_host_role():
    errors = lint_image_request({
        "visual_role": "evidence_object",
        "positive_prompt": "A close view of a sealed document",
        "host_reference_assets": ["canonical_seonbi.png"],
        "overlay_text": [],
    })
    assert any("host reference" in error for error in errors)


def test_lint_accepts_clean_reconstruction_request():
    errors = lint_image_request({
        "visual_role": "historical_reconstruction",
        "positive_prompt": "Late Joseon royal council, historical actors discussing an order, hand drawn doodle",
        "host_reference_assets": [],
        "overlay_text": ["renderer only"],
    })
    assert errors == []
