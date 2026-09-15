from __future__ import annotations

import re
from typing import Any


_LABEL_LANGUAGE = re.compile(r"\b(text|caption|label|sign|signage|written|date)\b", re.IGNORECASE)


def lint_image_request(request: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    positive = str(request.get("positive_prompt", ""))
    role = str(request.get("visual_role", ""))
    host_references = [item for item in request.get("host_reference_assets", []) if item]

    if re.search(r"\d", positive):
        errors.append("positive prompt contains a digit")
    if _LABEL_LANGUAGE.search(positive):
        errors.append("positive prompt contains generated label language")
    if role != "host_explainer" and host_references:
        errors.append("host reference is allowed only for host_explainer")
    for overlay in request.get("overlay_text", []):
        if overlay and str(overlay) in positive:
            errors.append("renderer overlay text leaked into positive prompt")
    return errors


def require_clean_image_request(request: dict[str, Any]) -> None:
    errors = lint_image_request(request)
    if errors:
        raise ValueError("; ".join(errors))
