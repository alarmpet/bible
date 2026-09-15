from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class GeneratedTextInspection:
    status: str
    findings: list[dict[str, Any]]
    error: str = ""


def rapidocr_result_to_findings(result: Any) -> list[dict[str, Any]]:
    text_values = getattr(result, "txts", None)
    score_values = getattr(result, "scores", None)
    box_values = getattr(result, "boxes", None)
    texts = [] if text_values is None else list(text_values)
    scores = [] if score_values is None else list(score_values)
    boxes = [] if box_values is None else list(box_values)
    findings = []
    for index, text in enumerate(texts):
        box = boxes[index].tolist() if index < len(boxes) and hasattr(boxes[index], "tolist") else (boxes[index] if index < len(boxes) else [])
        findings.append({
            "text": str(text),
            "confidence": float(scores[index]) if index < len(scores) else 0.0,
            "bbox": box,
        })
    return findings


def build_rapidocr_adapter() -> Callable[[Path], list[dict[str, Any]]] | None:
    try:
        from rapidocr import RapidOCR
    except ImportError:
        return None
    engine = RapidOCR()

    def run(image_path: Path) -> list[dict[str, Any]]:
        result = engine(str(image_path))
        return rapidocr_result_to_findings(result)

    return run


def inspect_generated_text(
    image_path: Path,
    ocr: Callable[[Path], list[dict[str, Any]]] | None,
    *,
    confidence_threshold: float = 0.70,
) -> GeneratedTextInspection:
    if ocr is None:
        return GeneratedTextInspection("REVIEW_REQUIRED", [], "local OCR engine unavailable")
    try:
        raw_findings = ocr(Path(image_path)) or []
    except Exception as error:
        return GeneratedTextInspection("REVIEW_REQUIRED", [], f"OCR execution failed: {error}")
    findings = [
        {
            "text": str(item.get("text", "")),
            "confidence": float(item.get("confidence", 0.0)),
            "bbox": item.get("bbox", []),
        }
        for item in raw_findings
        if str(item.get("text", "")).strip()
    ]
    actionable = [item for item in findings if item["confidence"] >= confidence_threshold]
    return GeneratedTextInspection("FAIL" if actionable else "PASS", findings)


def inspect_frame_visibility_gate(
    image_path: Path,
    scene_role: str = "opening_group",
) -> dict[str, Any]:
    """Evaluate Gate 8 visibility on the given image file."""
    from lib.asset_contract import evaluate_frame_visibility_from_file
    return evaluate_frame_visibility_from_file(image_path, scene_role=scene_role)

