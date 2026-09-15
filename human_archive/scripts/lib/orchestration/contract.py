"""Parse the reviewer output contract.

Reviewers answer in four fixed sections. Parsing them is what makes disagreement
mechanical: verdicts can be tabled, findings listed side by side, and reported numbers
compared digit for digit instead of by reading three documents and forming an impression.

The parser is deliberately forgiving about everything except structure. A model that
wanders off the format should surface as a malformed answer the round can see, not as a
silently empty one -- an unparsed reviewer that reads as "no findings" is the same
false-confidence failure this whole layer is built against.

Ported 2026-09-15 from D:\\all-manage\\tools\\orchestration\\contract.py (verbatim, this
module is domain-agnostic) as part of
docs/superpowers/plans/2026-09-15-human-archive-nollam-script-visual-motion-multi-llm-overhaul-plan.md
Task 2.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

VERDICTS = ("SOUND", "DEFECTIVE", "CANNOT_DETERMINE")
# Not anchored to line start. Providers prepend streaming narration, and Grok glues it
# directly onto the first heading ("...확인하겠습니다.## VERDICT"), which an anchored
# pattern misses -- the answer then reads as unparseable when it was in fact well formed.
# Requiring end-of-line after the heading keeps the match specific enough.
_SECTION = re.compile(r"##[ \t]+(VERDICT|FINDINGS|NUMBERS|UNCERTAINTY)[ \t]*(?=\n|$)")
_SEVERITY = re.compile(r"^-\s*\[(P[012])\]\s*(.+)$")
_BARE_ITEM = re.compile(r"^-\s+(.*)$")


@dataclass(frozen=True)
class Finding:
    severity: str
    claim: str
    evidence: str = ""
    impact: str = ""

    @property
    def is_none(self) -> bool:
        return self.claim.strip().lower() in {"none", "no findings"}


@dataclass
class Answer:
    verdict: str = ""
    findings: list[Finding] = field(default_factory=list)
    numbers: dict[str, str] = field(default_factory=dict)
    uncertainty: str = ""
    malformed: list[str] = field(default_factory=list)

    @property
    def real_findings(self) -> list[Finding]:
        return [f for f in self.findings if not f.is_none]

    @property
    def worst_severity(self) -> str | None:
        real = self.real_findings
        return min((f.severity for f in real), default=None)


def _split_sections(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    marks = list(_SECTION.finditer(text))
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out[mark.group(1)] = text[mark.end():end].strip()
    return out


def _parse_finding(line: str) -> Finding | None:
    match = _SEVERITY.match(line)
    if match:
        severity, rest = match.group(1), match.group(2)
    else:
        bare = _BARE_ITEM.match(line)
        if not bare:
            return None
        severity, rest = "P2", bare.group(1)
    parts = [p.strip() for p in rest.split("|")]
    claim = parts[0]
    evidence = impact = ""
    for part in parts[1:]:
        lowered = part.lower()
        if lowered.startswith("evidence:"):
            evidence = part.split(":", 1)[1].strip()
        elif lowered.startswith("impact:"):
            impact = part.split(":", 1)[1].strip()
    return Finding(severity=severity, claim=claim, evidence=evidence, impact=impact)


def _parse_numbers(block: str) -> dict[str, str]:
    numbers: dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.count("|") < 3:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        metric, value = cells[0], cells[1]
        # Skip the header and its underline.
        if not metric or metric.lower() == "metric" or set(metric) <= set("-: "):
            continue
        numbers[metric] = value
    return numbers


# The design roles answer in their own shape. Checking every answer against the review
# headings rejected two complete proposals as "stopped before answering" -- 7,019 and
# 11,839 characters of finished work, classified as truncation because the detector knew
# only one contract.
_DESIGN_SECTION = re.compile(
    r"##[ \t]+(HYPOTHESIS|MECHANISM|CONSTRUCTION|FALSIFICATION|NOVELTY|RISKS"
    r"|ASSESSMENT|KEEP|COMBINED)[ \t]*(?=\n|$)")


def has_contract(text: str, role: str | None = None) -> bool:
    """Whether this is an answer at all, as opposed to narration or a truncated run.

    The runner uses this to decide success. Non-empty output is not the same as an
    answer: a provider that stops two sentences into its reasoning still writes bytes to
    stdout, and counting that as a completed review is how a round loses a reviewer
    without noticing.

    `role` selects which contract to expect. Without it, either will do.
    """
    body = text or ""
    if role in ("designer", "critic"):
        return bool(_DESIGN_SECTION.search(body))
    if role is None:
        return bool(_SECTION.search(body) or _DESIGN_SECTION.search(body))
    return bool(_SECTION.search(body))


def parse(text: str) -> Answer:
    """Read one reviewer answer. Never raises; problems land in `malformed`."""
    answer = Answer()
    sections = _split_sections(text or "")
    if not sections:
        answer.malformed.append("no '## SECTION' headings found")
        return answer

    raw_verdict = sections.get("VERDICT", "").strip().splitlines()
    token = raw_verdict[0].strip().strip("*` ").upper() if raw_verdict else ""
    if token in VERDICTS:
        answer.verdict = token
    else:
        answer.malformed.append(f"verdict {token or '(empty)'!r} is not one of {VERDICTS}")

    if "FINDINGS" not in sections:
        answer.malformed.append("FINDINGS section missing")
    for line in sections.get("FINDINGS", "").splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        finding = _parse_finding(line)
        if finding is not None:
            answer.findings.append(finding)

    answer.numbers = _parse_numbers(sections.get("NUMBERS", ""))
    answer.uncertainty = sections.get("UNCERTAINTY", "").strip()
    return answer
