from dataclasses import dataclass, field


ALLOWED_VISUAL_ROLES = {
    "host_explainer",
    "historical_reconstruction",
    "evidence_object",
    "diagram_metaphor",
    "atmosphere",
}

@dataclass(frozen=True)
class VisualRoleDecision:
    role: str
    host_mode: str
    overlay_text: tuple[str, ...] = field(default_factory=tuple)
    era_context: str = "late Joseon royal court"
    rationale: str = ""

def classify_visual_role(scene: dict) -> VisualRoleDecision:
    beat = scene.get("beat", "body")
    if beat in {"hook", "roadmap", "analogy", "insight", "outro"}:
        return VisualRoleDecision("host_explainer", "full", rationale=f"beat={beat}")
    if beat == "source_commentary":
        return VisualRoleDecision("evidence_object", "absent", rationale="source commentary")
    return VisualRoleDecision("historical_reconstruction", "absent", rationale="fact-bearing narration")

def validate_role_mix(scenes: list[dict]) -> None:
    if not scenes:
        raise ValueError("scenes must not be empty")
    roles = [s.get("visual_role", s.get("role")) for s in scenes]
    unknown = sorted({role for role in roles if role not in ALLOWED_VISUAL_ROLES})
    if unknown:
        raise ValueError(f"unsupported visual role: {unknown}")
    for scene, role in zip(scenes, roles):
        host_mode = scene.get("host_mode", "absent")
        if role == "host_explainer" and host_mode != "full":
            raise ValueError("host_explainer requires host_mode=full")
        if role != "host_explainer" and host_mode != "absent":
            raise ValueError(f"non-host role {role} requires host_mode=absent")

    host = sum(role == "host_explainer" for role in roles)
    ratio = host / len(scenes)
    if ratio < 0.15:
        raise ValueError(f"host presence {ratio:.1%} is below 15%")
    if ratio > 0.25:
        raise ValueError(f"host presence {ratio:.1%} exceeds 25%")

    consecutive = 0
    for role in roles:
        consecutive = consecutive + 1 if role == "host_explainer" else 0
        if consecutive > 2:
            raise ValueError("more than two consecutive host scenes")

    evidence = sum(role in {"historical_reconstruction", "evidence_object"} for role in roles)
    if evidence / len(scenes) < 0.60:
        raise ValueError("historical/evidence scene ratio below 60%")
