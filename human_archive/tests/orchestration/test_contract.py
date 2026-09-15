"""A reviewer whose answer fails to parse must read as malformed, never as clean.

That distinction is the whole point: "no findings" and "we could not read the answer"
lead to opposite decisions, and collapsing them is how a round would quietly pass.

Ported 2026-09-15 from D:\\all-manage\\tests\\orchestration\\test_contract.py verbatim
(contract.py is domain-agnostic), only the import path changed.
"""

from __future__ import annotations

import sys
from pathlib import Path

_LIB_DIR = Path(__file__).resolve().parents[2] / "scripts" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from orchestration.contract import parse  # noqa: E402

WELL_FORMED = """## VERDICT
DEFECTIVE

## FINDINGS
- [P0] scene reuses shot_002's image for an unrelated claim | evidence: image_request_manifest.json:shot_014 | impact: narration and image no longer match
- [P1] visual_prompt truncates narration at 40 chars | evidence: historical_parallel_engine.py:806 | impact: scene content is generic, not claim-specific

## NUMBERS
| metric | value | how obtained |
|---|---|---|
| unique claim coverage | 0.62 | recomputed from claim_ids |
| scenes reviewed | 14 | len(shots) |

## UNCERTAINTY
Could not verify the primary source for claim CLM-004.
"""


def test_parses_a_well_formed_answer() -> None:
    a = parse(WELL_FORMED)
    assert a.verdict == "DEFECTIVE"
    assert not a.malformed
    assert len(a.real_findings) == 2
    assert a.worst_severity == "P0"
    assert a.numbers["unique claim coverage"] == "0.62"
    assert a.numbers["scenes reviewed"] == "14"
    assert "CLM-004" in a.uncertainty


def test_none_is_not_a_finding() -> None:
    a = parse("## VERDICT\nSOUND\n\n## FINDINGS\n- none\n\n## NUMBERS\n\n## UNCERTAINTY\n")
    assert a.verdict == "SOUND"
    assert a.real_findings == []
    assert a.worst_severity is None
    assert not a.malformed


def test_prose_answer_is_malformed_not_clean() -> None:
    a = parse("I looked at the script and it seems fine to me.")
    assert a.verdict == ""
    assert a.real_findings == []
    assert a.malformed, "an unparsed answer must not read as a clean pass"


def test_bad_verdict_token_is_flagged() -> None:
    a = parse("## VERDICT\nLOOKS GOOD\n\n## FINDINGS\n- none\n")
    assert a.verdict == ""
    assert any("not one of" in m for m in a.malformed)


def test_missing_findings_section_is_flagged() -> None:
    a = parse("## VERDICT\nSOUND\n\n## NUMBERS\n\n## UNCERTAINTY\nnone\n")
    assert a.verdict == "SOUND"
    assert any("FINDINGS" in m for m in a.malformed)


def test_finding_without_severity_defaults_to_p2() -> None:
    a = parse("## VERDICT\nDEFECTIVE\n\n## FINDINGS\n- something is off | evidence: x.py:1\n")
    assert a.real_findings[0].severity == "P2"
    assert a.real_findings[0].evidence == "x.py:1"


def test_number_table_header_is_not_a_metric() -> None:
    a = parse(WELL_FORMED)
    assert "metric" not in a.numbers
    assert all(not set(k) <= set("-: ") for k in a.numbers)


def test_verdict_survives_markdown_emphasis() -> None:
    assert parse("## VERDICT\n**SOUND**\n\n## FINDINGS\n- none\n").verdict == "SOUND"


def test_empty_input_is_malformed() -> None:
    assert parse("").malformed


def test_streaming_narration_before_the_first_heading_is_discarded() -> None:
    """Grok emits progress narration and glues it onto the first heading with no line
    break. The first real round read as malformed for exactly this reason, while the
    answer underneath it was well formed."""
    narrated = "I will check the claim IDs without reading the code." + WELL_FORMED
    a = parse(narrated)
    assert a.verdict == "DEFECTIVE"
    assert not a.malformed
    assert len(a.real_findings) == 2
    assert "I will check" not in a.uncertainty


def test_headings_are_still_required_to_end_the_line() -> None:
    a = parse("The ## VERDICT section should say SOUND but I never wrote one.")
    assert a.malformed


def test_has_contract_distinguishes_an_answer_from_narration() -> None:
    from orchestration.contract import has_contract
    assert has_contract(WELL_FORMED)
    assert has_contract("preamble text." + WELL_FORMED)
    assert not has_contract("I'll start from the spec. Next I'll read the rest of it.")
    assert not has_contract("")


PROPOSAL = """## HYPOTHESIS
The record-absence claim is best shown as two closed archival record cases, not a crowd scene.

## MECHANISM
The narration argues an absence of evidence, not an event; a literal reenactment would assert something the sources do not support.

## CONSTRUCTION
focal_subject: two sealed official record cases; place: archive interior; era: Joseon court records.

## FALSIFICATION
If a human reviewer judges the metaphor unclear from the image alone, this design fails.

## RISKS
An abstract prop may read as unrelated without the narration playing alongside it.
"""


def test_a_proposal_is_recognised_as_an_answer() -> None:
    """Two finished proposals were classified as "stopped before answering" upstream
    because the detector knew only the review contract."""
    from orchestration.contract import has_contract
    assert has_contract(PROPOSAL, "designer")
    assert has_contract(PROPOSAL, "critic")
    assert has_contract(PROPOSAL)          # role unknown: either contract will do


def test_a_review_answer_is_not_accepted_from_a_designer() -> None:
    from orchestration.contract import has_contract
    assert not has_contract(WELL_FORMED, "designer")


def test_a_proposal_is_not_accepted_from_a_reviewer() -> None:
    from orchestration.contract import has_contract
    assert not has_contract(PROPOSAL, "adversary")


def test_narration_is_rejected_under_either_contract() -> None:
    from orchestration.contract import has_contract
    narration = "I'll start by reading the spec, then design the scene."
    assert not has_contract(narration, "designer")
    assert not has_contract(narration, "adversary")
    assert not has_contract(narration)
