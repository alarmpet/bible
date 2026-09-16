from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from lib.ep02_visual_scene_catalog import EP02_SCENES_BY_DIGEST
from lib.schema_validation import load_schema, validate_json

MODES = ("historical_reconstruction", "evidence_artifact", "place_establishing", "diagram_metaphor", "atmosphere", "character_action", "host_chapter_hinge", "analogy_explainer")


def _specific_scene(text: str) -> dict[str, object]:
    curated = EP02_SCENES_BY_DIGEST.get(text)
    if curated is not None:
        return dict(curated)
    rules = [
        (("실록에도", "난동"), "evidence_artifact", ["two sealed archive cases", "empty evidence tray", "two archivists"], "two archivists compare two closed unmarked archive cases, then indicate an empty evidence tray; every surface is blank", "royal archive storage room", "artifact_close_push"),
        (("기록과 이야기",), "analogy_explainer", ["wooden theatre mask", "sealed archive chest", "diverging floor path"], "a wooden theatre mask and a sealed archive chest sit at the ends of one diverging palace-stone path, with no panels or labels", "quiet palace courtyard", "analogy_pan"),
        (("취선당", "신당"), "place_establishing", ["Chwiseondang west courtyard", "small shrine alcove", "inspecting officials"], "palace officials inspect a discreet shrine alcove in the west courtyard while a closed royal palanquin waits farther back", "Chwiseondang west courtyard", "place_sweep"),
        (("자진 명령",), "evidence_artifact", ["two sealed scroll tubes", "brass balance", "red and blue cords"], "two completely closed unmarked scroll tubes tied with different colored cords rest on a brass balance, with no pages visible", "sparse royal evidence chamber", "artifact_close_push"),
        (("사료와 연구", "야담"), "analogy_explainer", ["theatre mask", "sealed archive chest", "brass balance"], "a theatrical wooden mask and a sealed blank archive chest are weighed on one brass balance in a single coherent room", "neutral palace study alcove without furniture", "analogy_pan"),
        (("한쪽은 극적인",), "analogy_explainer", ["dramatic stage mask", "closed royal command case", "single balance beam"], "a dramatic stage mask and a closed unmarked royal command case hang from opposite sides of one balance beam", "plain ivory exhibition alcove", "analogy_pan"),
        (("기록의 침묵",), "evidence_artifact", ["empty archive cubby", "sealed cases", "searching archivists"], "two archivists search a row of sealed blank cases and pause at one conspicuously empty cubby; no writing or open books", "royal archive aisle", "artifact_close_push"),
        (("약사발",), "analogy_explainer", ["overturned stage bowl", "closed archive chest", "untouched evidence shelf"], "an overturned theatrical medicine bowl lies near a stage curtain while a separate sealed blank archive chest remains untouched in the same room", "palace rehearsal chamber", "analogy_pan"),
        (("기억한 최후",), "analogy_explainer", ["fading stage curtain", "sealed archive chest", "two converging paths"], "a fading theatre curtain and a solid sealed archive chest stand where two stone paths converge, without text or panels", "empty palace courtyard", "analogy_pan"),
        (("통명전", "흉물"), "character_action", ["Tongmyeongjeon courtyard", "wrapped buried bundle", "palace investigators"], "three palace investigators carefully uncover one cloth-wrapped bundle from disturbed soil beside the hall foundation", "Tongmyeongjeon courtyard", "reenactment_push"),
        (("두 장소",), "place_establishing", ["two palace courtyards", "connecting covered walkway", "inspection teams"], "one wide palace compound view shows two distinct courtyards linked by a covered walkway, with a small inspection team at each site", "royal palace compound", "route_pan"),
        (("죄목", "명분"), "diagram_metaphor", ["small black stone", "large royal balance", "palace gate shadow"], "a small black stone tips an oversized royal balance whose long shadow reaches the palace gate, with no symbols or writing", "minimal palace forecourt", "diagram_reveal"),
        (("왕권",), "historical_reconstruction", ["King Sukjong", "kneeling officials", "sealed command case"], "King Sukjong advances a sealed unmarked command case across the council floor while officials kneel in opposing rows", "royal council hall", "reenactment_push"),
        (("대신들은",), "historical_reconstruction", ["petitioning ministers", "King Sukjong", "closed petition cases"], "senior ministers kneel with closed blank petition cases and raise open hands while King Sukjong remains firm beyond them", "royal council hall", "reenactment_push"),
        (("서로 다른 날짜",), "evidence_artifact", ["two sealed record cases", "dawn light", "evening light"], "two closed unmarked record cases occupy separate shelf bays, one lit by dawn light and the other by evening light, no labels", "royal archive aisle", "artifact_close_push"),
        (("왕실 운영 원칙",), "diagram_metaphor", ["palace gate beam", "locking wooden pin", "royal courtyard"], "a large wooden locking pin settles into the crossbeam of a palace gate as attendants stand back, forming one clear institutional metaphor", "royal palace gate", "diagram_reveal"),
        (("무속 사건",), "historical_reconstruction", ["shrine alcove", "wrapped ritual objects", "palace investigators"], "palace investigators uncover a small shrine alcove with wrapped ritual objects and covered vessels, all surfaces blank", "Chwiseondang west courtyard", "reenactment_push"),
        (("역사가 어렵다",), "host_chapter_hinge", ["open palace path", "small history objects", "clear host space"], "small palace roof, sealed archive chest, and brass balance form a welcoming vignette on the left with a clean open path", "bright palace courtyard", "host_hinge"),
        (("사약", "발악"), "host_chapter_hinge", ["intact medicine bowl", "quiet palace room", "myth correction"], "an intact unmarked medicine bowl rests safely on a low pedestal at left in a calm palace room, contradicting theatrical chaos", "quiet palace room", "host_hinge"),
    ]
    for needles, mode, anchors, action, place, motion in rules:
        if all(needle in text for needle in needles):
            return {"mode": mode, "anchors": anchors, "action": action, "place": place, "motion": motion}
    raise ValueError(f"No concrete visual scene rule for narration: {text[:160]}")


def build_fallback_brief(shot: dict, sentence_texts: dict[str, str]) -> dict:
    digest = " ".join(sentence_texts.get(span.get("sentence_id"), "") for span in shot.get("sentence_spans", [])).strip()
    scene = _specific_scene(digest)
    return {
        "shot_id": shot["shot_id"], "narration_digest": digest[:240], "visual_mode": scene["mode"],
        "semantic_anchors": scene["anchors"], "focal_subject": scene["anchors"][0], "action": scene["action"],
        "place": scene["place"], "era": "Joseon period", "shot_scale": "medium wide full-frame 16:9",
        "camera": "documentary observational framing, complete bodies, coherent single scene", "foreground": "one narration-specific prop only",
        "midground": "the main narrated action", "background": "specific uncluttered period architecture",
        "continuity_group": f"chapter-{shot.get('chapter', 1)}", "reference_asset_ids": [],
        "prop_motifs": list(scene["anchors"][:2]), "text_overlay_policy": "all surfaces blank and unmarked; no generated text, letters, digits, labels, seals, signatures, watermark, or service marks",
        "overlay_items": [], "motion_profile": scene["motion"],
        "safety_treatment": "no sensational violence, no presenter outside host mode, no open written pages, no collage or split panel",
    }


class AntigravityCliVisualBriefProvider:
    """Authoritative Antigravity CLI (`agy`) & Agent Visual Brief Provider."""

    def __init__(
        self,
        repo_root: Path,
        runner=subprocess.run,
        *,
        model: str | None = None,
    ):
        self.repo_root = Path(repo_root)
        self.runner = runner
        self.model = model

    def generate(self, prompt: str, output_schema_path: Path) -> dict:
        import shutil
        output_schema_path = Path(output_schema_path)
        schema = load_schema(output_schema_path)

        agy_cmd = shutil.which("agy") or shutil.which("antigravity")
        if agy_cmd:
            try:
                args = [agy_cmd, "generate", "--format", "json"]
                if self.model:
                    args.extend(["--model", self.model])
                completed = self.runner(
                    args,
                    input=prompt,
                    text=True,
                    encoding="utf-8",
                    capture_output=True,
                    shell=False,
                )
                if completed.returncode == 0:
                    result = json.loads(completed.stdout)
                    validate_json(result, schema)
                    return result
            except Exception:
                pass

        raise RuntimeError(
            "Antigravity CLI visual brief generation requires an active Antigravity Agent or valid response artifact."
        )


class CodexCliVisualBriefProvider:
    """Legacy provider (fallback)."""
    def __init__(
        self,
        repo_root: Path,
        runner=subprocess.run,
        *,
        model: str | None = None,
        reasoning_effort: str | None = None,
    ):
        self.repo_root = Path(repo_root)
        self.runner = runner
        self.model = model
        self.reasoning_effort = reasoning_effort

    def generate(self, prompt: str, output_schema_path: Path) -> dict:
        output_schema_path = Path(output_schema_path)
        with tempfile.TemporaryDirectory(prefix="visual-brief-") as temp_dir:
            output_path = Path(temp_dir) / "visual-brief-response.json"
            # 2026-09-16: found live -- a bare "codex" with shell=False fails
            # with WinError 2 on Windows when codex is installed via npm (the
            # default), because that install is a codex.CMD shim and
            # CreateProcess (unlike a shell) does not apply PATHEXT
            # resolution on its own. run_consensus_round.py's codex_cmd()
            # already resolves this correctly via shutil.which() -- mirror
            # that instead of hardcoding the bare name.
            codex_exe = shutil.which("codex")
            if not codex_exe:
                raise FileNotFoundError("codex is not on PATH")
            args = [
                codex_exe,
                "exec",
                "--ephemeral",
                "--sandbox",
                "read-only",
            ]
            if self.model:
                args.extend(["--model", self.model])
            if self.reasoning_effort:
                args.extend(
                    ["-c", f"model_reasoning_effort={self.reasoning_effort}"]
                )
            args.extend([
                "--output-schema",
                str(output_schema_path),
                "--output-last-message",
                str(output_path),
                "--cd",
                str(self.repo_root),
                "-",
            ])
            completed = self.runner(
                args,
                input=prompt,
                text=True,
                encoding="utf-8",
                capture_output=True,
                shell=False,
            )
            if completed.returncode != 0:
                detail = str(completed.stderr or completed.stdout or "unknown error")
                raise RuntimeError(f"Visual brief generation failed: {detail.strip()}")
            if not output_path.exists():
                raise RuntimeError("Visual brief generation produced no output file")
            try:
                result = json.loads(output_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Visual brief output is not valid JSON: {exc}") from exc
            validate_json(result, load_schema(output_schema_path))
            return result


class JsonFileVisualBriefProvider:
    def __init__(self, path: Path):
        self.path = Path(path)

    def generate(self, prompt: str, output_schema_path: Path) -> dict:
        try:
            result = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Visual brief response is not valid JSON: {exc}") from exc
        validate_json(result, load_schema(Path(output_schema_path)))
        return result
