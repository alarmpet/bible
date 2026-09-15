# -*- coding: utf-8 -*-
"""Fan one question out to independent reviewers/designers, keep their answers apart, and
table the disagreement.

The design constraint is that agreement is not evidence. So this runner never merges,
summarises, or votes: each participant's answer is written verbatim to its own file, and
`diverge` builds a comparison that shows where they disagree rather than a conclusion that
hides it. All participants agreeing on a wrong scene/claim is the failure mode this project
already paid for once (`scripts/tri_model_debate_engine.py`'s hardcoded "consensus_score").

Two of the three default participants are subprocesses (Codex/GPT, Grok). The third is the
orchestrating Claude session, which cannot invoke itself, so `start`/`propose` write its
prompt to the round directory and print the assigned role for the session to pick up.
Roles rotate with the round index -- leaving one participant permanently in the proposer
seat bakes its bias into every result.

Ported 2026-09-15 from D:\\all-manage\\tools\\orchestration\\run_round.py, adapted for
human_archive: default participants are (claude, codex, grok); a fourth ("gemini", via the
`agy`/`antigravity` CLI already used by lib/visual_brief_provider.py) is a documented
extension point for vision-heavy rounds (scene visual briefs, motion QA) per
docs/superpowers/plans/2026-09-15-human-archive-nollam-script-visual-motion-multi-llm-overhaul-plan.md
Task 2 / §5.6, not yet wired into `_invoke` below.

    python human_archive/scripts/run_consensus_round.py start --topic ep03-shot012-factcheck --spec spec.md
    python human_archive/scripts/run_consensus_round.py diverge --round human_archive/audit/orchestration/<dir>
"""

from __future__ import annotations

import argparse
import asyncio  # noqa: F401 - kept for parity with the ported module; not used directly
import concurrent.futures as futures
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
_LIB_DIR = _SCRIPTS_DIR / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))
from orchestration.contract import Answer, has_contract, parse  # noqa: E402
from orchestration.prompt_assembly import ROLES, assemble  # noqa: E402

ROOT = _SCRIPTS_DIR.parent  # .../human_archive
ROUNDS = ROOT / "audit" / "orchestration"
PARTICIPANTS = ("claude", "codex", "grok")
DEFAULT_TIMEOUT = 1800
GROK_MAX_TURNS = 80
# Pinned to this machine's global `codex` config (~/.codex/config.toml) as of 2026-09-15.
# Pinning (rather than inheriting the global config silently) keeps a round comparable
# with the ones before it and leaves the user's global config alone. Re-verify this value
# with `codex --version` / `~/.codex/config.toml` if codex reports an unknown model.
CODEX_MODEL = "gpt-5.6-luna"


def say(message: str) -> None:
    """Print without ever letting the console's codepage raise.

    stdout here can be cp949 (confirmed directly on this machine, 2026-09-15: a plain
    em-dash in a markdown file raised UnicodeEncodeError through this exact code path
    during testing). A single non-ASCII character in a status line is enough to abort the
    run, and provider output is not ours to sanitise, so anything unprintable is replaced
    rather than allowed to propagate.
    """
    encoding = sys.stdout.encoding or "utf-8"
    sys.stdout.write(message.encode(encoding, errors="replace").decode(encoding) + "\n")


@dataclass
class Run:
    """One provider invocation. stderr is carried even when the call succeeded: a
    transient-failure diagnosis needs whatever the provider wrote there, and it is
    otherwise the first thing discarded."""
    ok: bool
    text: str
    detail: str = ""
    stderr: str = ""


@dataclass
class Outcome:
    participant: str
    role: str
    ok: bool
    text: str
    seconds: float
    detail: str = ""
    stderr: str = ""


def _exe(name: str, fallback: str | None = None) -> str:
    found = shutil.which(name)
    if found:
        return found
    if fallback and Path(fallback).exists():
        return fallback
    raise FileNotFoundError(f"{name} is not on PATH")


def codex_cmd(out_file: Path, exe: str = "codex") -> list[str]:
    """A review round never runs Codex outside the read-only sandbox.

    The model is pinned rather than inherited from `~/.codex/config.toml`. A round whose
    reviewer silently changes between runs cannot be compared with an earlier one, and the
    global config is the user's to set for their own work.
    """
    return [
        exe, "exec",
        "-s", "read-only",
        "-m", CODEX_MODEL,
        "-C", str(ROOT),
        "--skip-git-repo-check",
        "-o", str(out_file),
        "-",
    ]


def grok_cmd(prompt_file: Path, exe: str = "grok") -> list[str]:
    """`--prompt-file` is mandatory: without a prompt flag Grok opens an interactive
    session and never returns, hanging the round.

    `auto` rather than `default`, because `default` asks for approval and a
    non-interactive run has nobody to ask.
    """
    return [
        exe,
        "--prompt-file", str(prompt_file),
        "--output-format", "plain",
        "--permission-mode", "auto",
        "--disable-web-search",                # answers must come from the provided spec
        "--max-turns", str(GROK_MAX_TURNS),
    ]


def _run_codex(prompt: str, out_file: Path, timeout: int) -> Run:
    """Codex reads the prompt on stdin; passing it as an argument breaks on the leading
    '#' and the '--' sequences inside, which the arg parser reads as flags."""
    cmd = codex_cmd(out_file, _exe("codex"))
    proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
    text = out_file.read_text(encoding="utf-8") if out_file.exists() else ""
    if not text.strip():
        return Run(False, "", f"exit {proc.returncode}; no output", proc.stderr)
    return Run(True, text, "", proc.stderr)


def _run_grok(prompt: str, prompt_file: Path, timeout: int) -> Run:
    prompt_file.write_text(prompt, encoding="utf-8")
    cmd = grok_cmd(prompt_file, _exe("grok", r"C:\Users\shs\.grok\bin\grok.exe"))
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT),
                           encoding="utf-8", errors="replace", timeout=timeout)
    if not proc.stdout.strip():
        return Run(False, "", f"exit {proc.returncode}", proc.stderr)
    return Run(True, proc.stdout, "", proc.stderr)


# Upstream capacity and rate errors say nothing about the question being reviewed.
TRANSIENT = re.compile(
    r"at capacity|rate.?limit|overloaded|temporarily unavailable|503|429|timed out",
    re.IGNORECASE,
)


def is_transient(detail: str) -> bool:
    return bool(TRANSIENT.search(detail or ""))


def _attempt(participant: str, role: str, prompt: str, round_dir: Path,
             timeout: int) -> Run:
    try:
        if participant == "codex":
            run = _run_codex(prompt, round_dir / f"_{role}.codex.raw.md", timeout)
        elif participant == "grok":
            run = _run_grok(prompt, round_dir / f"_{role}.grok.prompt.txt", timeout)
        else:
            raise ValueError(f"{participant} is not a subprocess participant")
    except subprocess.TimeoutExpired:
        return Run(False, "", f"timed out after {timeout}s")
    except Exception as exc:  # noqa: BLE001 - one provider failing must not lose the others
        return Run(False, "", f"{type(exc).__name__}: {exc}")

    # Bytes on stdout are not an answer. A provider that stops partway through its
    # reasoning still writes something, and counting that as a completed review is
    # exactly the "consensus_score without a call" failure this engine replaces.
    if run.ok and not has_contract(run.text, role):
        return Run(False, run.text,
                   f"stopped before answering: no output-contract sections in "
                   f"{len(run.text)} characters", run.stderr)
    return run


def _invoke(participant: str, role: str, prompt: str, round_dir: Path, timeout: int,
            retries: int = 1, backoff: float = 20.0) -> Outcome:
    started = dt.datetime.now()
    run = _attempt(participant, role, prompt, round_dir, timeout)
    attempt = 0
    while (not run.ok and attempt < retries
           and is_transient(f"{run.detail}\n{run.stderr}")):
        attempt += 1
        say(f"  {participant:<8} transient failure, retry {attempt}/{retries} "
            f"in {backoff:.0f}s")
        time.sleep(backoff)
        run = _attempt(participant, role, prompt, round_dir, timeout)
    seconds = (dt.datetime.now() - started).total_seconds()
    detail = run.detail if run.ok else (
        f"[after {attempt} retry] {run.detail}" if attempt else run.detail)
    return Outcome(participant, role, run.ok, run.text, seconds, detail, run.stderr)


def assign(rotation: int) -> dict[str, str]:
    """Who plays which role this round. Rotating stops one participant's bias from
    becoming the house view."""
    return {p: ROLES[(i + rotation) % len(ROLES)] for i, p in enumerate(PARTICIPANTS)}


def start(args: argparse.Namespace) -> int:
    spec = Path(args.spec).read_text(encoding="utf-8")
    stamp = dt.date.today().isoformat()
    round_dir = Path(args.round_dir) if args.round_dir else ROUNDS / f"{stamp}-{args.topic}"
    round_dir.mkdir(parents=True, exist_ok=True)
    (round_dir / "spec.md").write_text(spec, encoding="utf-8")

    roles = assign(args.rotation)
    say(f"round      : {round_dir}")
    for participant, role in roles.items():
        say(f"  {participant:<8} -> {role}")

    claude_prompt = assemble(roles["claude"], spec)
    (round_dir / f"_{roles['claude']}.claude.prompt.md").write_text(claude_prompt,
                                                                     encoding="utf-8")

    subprocess_participants = [p for p in PARTICIPANTS if p != "claude"]
    results: list[Outcome] = []
    with futures.ThreadPoolExecutor(max_workers=max(1, len(subprocess_participants))) as pool:
        pending = {
            pool.submit(_invoke, p, roles[p], assemble(roles[p], spec), round_dir,
                        args.timeout): p
            for p in subprocess_participants
        }
        for future in futures.as_completed(pending):
            results.append(future.result())

    ordered = sorted(results, key=lambda o: o.participant)
    for outcome in ordered:
        target = round_dir / f"{outcome.role}.{outcome.participant}.md"
        if outcome.stderr.strip():
            (round_dir / f"_{outcome.role}.{outcome.participant}.stderr.txt").write_text(
                outcome.stderr, encoding="utf-8")
        if outcome.ok:
            target.write_text(outcome.text, encoding="utf-8")
        else:
            body = outcome.detail
            if outcome.text.strip():
                body += f"\n\n--- captured output ({len(outcome.text)} chars) ---\n{outcome.text}"
            target.with_suffix(".FAILED.md").write_text(body, encoding="utf-8")

    (round_dir / "assignment.json").write_text(json.dumps({
        "topic": args.topic,
        "date": stamp,
        "rotation": args.rotation,
        "roles": roles,
        "timeout_seconds": args.timeout,
        "results": [{"participant": o.participant, "role": o.role, "ok": o.ok,
                     "seconds": round(o.seconds, 1), "detail": o.detail}
                    for o in ordered],
    }, indent=2), encoding="utf-8")

    for outcome in ordered:
        if outcome.ok:
            parsed = parse(outcome.text)
            flag = f" [malformed: {'; '.join(parsed.malformed)}]" if parsed.malformed else ""
            say(f"  {outcome.participant:<8} {outcome.seconds:>6.1f}s  "
                f"{parsed.verdict or '?':<16} {len(parsed.real_findings)} findings{flag}")
        else:
            first = outcome.detail.splitlines()[-1] if outcome.detail else "unknown"
            say(f"  {outcome.participant:<8} {outcome.seconds:>6.1f}s  FAILED: {first}")

    claude_role = roles["claude"]
    prompt_path = round_dir / f"_{claude_role}.claude.prompt.md"
    answer_path = round_dir / f"{claude_role}.claude.md"
    say(f"\nClaude plays {claude_role}.")
    say(f"  prompt -> {prompt_path}")
    say(f"  answer -> {answer_path}")
    say(f"  then   -> python human_archive/scripts/run_consensus_round.py diverge --round {round_dir}")
    return 0


def _fan_out(round_dir: Path, role: str, text: str, timeout: int,
             stem: str) -> list[Outcome]:
    """Run the subprocess participants on the same prompt and persist whatever comes
    back. Everything is written before anything is printed."""
    subs = [p for p in PARTICIPANTS if p != "claude"]
    results: list[Outcome] = []
    with futures.ThreadPoolExecutor(max_workers=max(1, len(subs))) as pool:
        pending = [pool.submit(_invoke, p, role, assemble(role, text), round_dir, timeout)
                   for p in subs]
        for future in futures.as_completed(pending):
            results.append(future.result())
    ordered = sorted(results, key=lambda o: o.participant)
    for outcome in ordered:
        if outcome.stderr.strip():
            (round_dir / f"_{stem}.{outcome.participant}.stderr.txt").write_text(
                outcome.stderr, encoding="utf-8")
        target = round_dir / f"{stem}.{outcome.participant}.md"
        if outcome.ok:
            target.write_text(outcome.text, encoding="utf-8")
        else:
            body = outcome.detail
            if outcome.text.strip():
                body += f"\n\n--- captured output ({len(outcome.text)} chars) ---\n{outcome.text}"
            target.with_suffix(".FAILED.md").write_text(body, encoding="utf-8")
    for outcome in ordered:
        state = "ok" if outcome.ok else f"FAILED: {outcome.detail.splitlines()[0]}"
        say(f"  {outcome.participant:<8} {outcome.seconds:>6.1f}s  {state}")
    return ordered


def check_independence(round_dir: Path, stem: str) -> list[str]:
    """Report any answer that existed while another participant was still writing.

    "Nobody sees the others" is always an instruction to the participants and never more.
    The round directory is on disk and the subprocesses can read it, so an answer written
    into it while another designer is still running is an answer that designer could read.
    Timestamps are the only evidence available after the fact and they are enough.
    Reported rather than raised: the round still happened, and a round that says it leaked
    is worth more than one that quietly did.
    """
    files = {p.stem.split(".")[-1]: p for p in round_dir.glob(f"{stem}.*.md")}
    if len(files) < 2:
        return []
    stamps = {who: p.stat().st_mtime for who, p in files.items()}
    last = max(stamps.values())
    exposed = sorted(who for who, t in stamps.items() if last - t > 30)
    if not exposed:
        return []
    order = ", ".join(f"{who} {dt.datetime.fromtimestamp(t):%H:%M:%S}"
                       for who, t in sorted(stamps.items(), key=lambda kv: kv[1]))
    say("  INDEPENDENCE: " + ", ".join(exposed) + " finished while someone else was "
        "still writing, and this directory is readable.")
    say(f"      {order}")
    say("      Treat agreement between these answers as unverified, not as evidence.")
    return exposed


def propose(args: argparse.Namespace) -> int:
    """Stage one: independent designs, nobody seeing the others."""
    problem = Path(args.problem).read_text(encoding="utf-8")
    stamp = dt.date.today().isoformat()
    round_dir = ROUNDS / f"{stamp}-{args.topic}"
    round_dir.mkdir(parents=True, exist_ok=True)
    (round_dir / "problem.md").write_text(problem, encoding="utf-8")
    (round_dir / "_designer.claude.prompt.md").write_text(
        assemble("designer", problem), encoding="utf-8")
    say(f"round    : {round_dir}")
    say("stage    : PROPOSE (all participants design independently)")
    _fan_out(round_dir, "designer", problem, args.timeout, "proposal")
    check_independence(round_dir, "proposal")
    say("\nClaude designs too.")
    say(f"  prompt -> {round_dir / '_designer.claude.prompt.md'}")
    say(f"  answer -> {round_dir / 'proposal.claude.md'}")
    say(f"  then   -> python human_archive/scripts/run_consensus_round.py critique --round {round_dir}")
    return 0


def critique(args: argparse.Namespace) -> int:
    """Stage two: everyone attacks every proposal, including their own, and says what
    they would keep. Rejecting all proposals is a failure of this stage, not a result."""
    round_dir = Path(args.round)
    problem = (round_dir / "problem.md").read_text(encoding="utf-8")
    proposals = sorted(round_dir.glob("proposal.*.md"))
    proposals = [p for p in proposals if not p.name.endswith(".FAILED.md")]
    if len(proposals) < 2:
        say(f"only {len(proposals)} proposal(s) in {round_dir}; nothing to cross-examine")
        return 1
    blocks = []
    for path in proposals:
        who = path.stem.split(".")[1]
        blocks.append(f"## Proposal from {who}\n\n{path.read_text(encoding='utf-8')}")
    packet = (problem + "\n\n---\n\n# The proposals\n\n"
              + "\n\n---\n\n".join(blocks))
    (round_dir / "_critique.packet.md").write_text(packet, encoding="utf-8")
    (round_dir / "_critic.claude.prompt.md").write_text(
        assemble("critic", packet), encoding="utf-8")
    say(f"round    : {round_dir}")
    say(f"stage    : CRITIQUE ({len(proposals)} proposals cross-examined)")
    _fan_out(round_dir, "critic", packet, args.timeout, "critique")
    say("\nClaude critiques too.")
    say(f"  prompt -> {round_dir / '_critic.claude.prompt.md'}")
    say(f"  answer -> {round_dir / 'critique.claude.md'}")
    return 0


def _collect(round_dir: Path) -> dict[str, Answer]:
    answers: dict[str, Answer] = {}
    for path in sorted(round_dir.glob("*.md")):
        if path.name.startswith("_") or path.name in {"spec.md", "problem.md",
                                                        "divergence.md", "verdict.md"}:
            continue
        if path.name.endswith(".FAILED.md"):
            continue
        parts = path.stem.split(".")
        if len(parts) != 2 or parts[0] not in ROLES + ("proposal", "critique"):
            continue
        answers[f"{parts[1]} ({parts[0]})"] = parse(path.read_text(encoding="utf-8"))
    return answers


# Reviewers report the same quantity at different precision. Comparing the strings made
# sensible near-matches read as "CONFLICT"; the tolerance is fixed in advance per round.
NUMERIC_TOLERANCE = 0.01


def _as_number(text: str) -> float | None:
    try:
        return float(str(text).strip().replace(",", "").rstrip("%"))
    except ValueError:
        return None


def _agreement(values: list[str]) -> tuple[str, bool]:
    """(status cell, agreed) for one metric's reported values."""
    if len(set(values)) == 1:
        return "**confirmed**", True
    numbers = [_as_number(v) for v in values]
    if any(n is None for n in numbers):
        return "**CONFLICT**", False
    lo, hi = min(numbers), max(numbers)
    scale = max(abs(lo), abs(hi))
    if scale == 0:
        return "**confirmed**", True
    spread = (hi - lo) / scale
    if spread <= NUMERIC_TOLERANCE:
        return f"**confirmed** ({spread:.1%})", True
    return f"**CONFLICT** ({spread:.1%})", False


def diverge(args: argparse.Namespace) -> int:
    round_dir = Path(args.round)
    answers = _collect(round_dir)
    if not answers:
        print(f"no participant answers found in {round_dir}", file=sys.stderr)
        return 1

    lines = [f"# Divergence -- {round_dir.name}", "",
             "Answers are compared, not merged. Where participants disagree the round is "
             "unresolved; it is not settled by majority.", "", "## Verdicts", "",
             "| participant | verdict | findings | worst | malformed |",
             "|---|---|---|--:|---|---|"]
    for name, answer in answers.items():
        lines.append(f"| {name} | {answer.verdict or '(unparsed)'} | "
                      f"{len(answer.real_findings)} | {answer.worst_severity or '-'} | "
                      f"{'; '.join(answer.malformed) or '-'} |")

    verdicts = {a.verdict for a in answers.values() if a.verdict}
    lines += ["", f"**Verdicts agree:** {'yes' if len(verdicts) <= 1 else 'NO -- ' + ', '.join(sorted(verdicts))}", ""]

    lines += ["## Findings", ""]
    for name, answer in answers.items():
        lines.append(f"### {name}")
        real = answer.real_findings
        if not real:
            lines += ["", "- none", ""]
            continue
        lines.append("")
        for finding in sorted(real, key=lambda f: f.severity):
            evidence = f" -- `{finding.evidence}`" if finding.evidence else ""
            lines.append(f"- **{finding.severity}** {finding.claim}{evidence}")
        lines.append("")

    metrics = sorted({m for a in answers.values() for m in a.numbers})
    conflicting = confirmed = 0
    if metrics:
        heads = list(answers)
        lines += ["## Numbers", "",
                  "A metric only one participant reported is **unconfirmed**, not agreed.",
                  "",
                  "| metric | " + " | ".join(heads) + " | status |",
                  "|---" * (len(heads) + 2) + "|"]
        for metric in metrics:
            values = [answers[h].numbers.get(metric, "-") for h in heads]
            given = [v for v in values if v != "-"]
            if len(given) < 2:
                status = "unconfirmed"
            else:
                status, agreed = _agreement(given)
                confirmed += agreed
                conflicting += not agreed
            lines.append(f"| {metric} | " + " | ".join(values) + f" | {status} |")
        lines += ["", f"Cross-confirmed metrics: **{confirmed}** of {len(metrics)}. "
                      f"Conflicts: **{conflicting}**.", ""]

    missing = sorted(p.name.split(".")[1] for p in round_dir.glob("*.FAILED.md"))
    absent = [p for p in PARTICIPANTS
              if not any(p == name.split(" ")[0] for name in answers)]

    status: list[str] = []
    if len(verdicts) > 1 or conflicting:
        status.append("**UNRESOLVED -- escalate to a human approval touchpoint.** "
                      "Participants disagree, and this layer does not adjudicate that "
                      "(see docs/orchestration/HARD_GATES.md).")
    else:
        status.append("No participant contradicted another. That is not the same as "
                      "corroboration: agreement is not evidence, and this round is only "
                      "as strong as its weakest independent check.")
    if metrics and confirmed == 0 and conflicting == 0:
        status.append(f"**No number was independently confirmed.** The participants "
                      f"reported {len(metrics)} metrics between them and not one in "
                      "common, so nothing here has been checked twice.")
    elif metrics and confirmed == 0:
        status.append("**No number was independently confirmed.** Every metric two "
                      "participants both reported disagrees.")
    if missing:
        status.append(f"**Incomplete round.** Participant(s) failed: {', '.join(missing)}. "
                      "A verdict reached without the adversary is not an adversarial result.")
    if absent:
        status.append(f"No answer from: {', '.join(absent)}.")
    lines += ["## Status", ""] + [f"- {s}" for s in status] + [""]
    unresolved = len(verdicts) > 1 or bool(conflicting)

    (round_dir / "divergence.md").write_text("\n".join(lines), encoding="utf-8")
    say(f"written -> {round_dir / 'divergence.md'}")
    say(f"  participants {len(answers)} | verdicts {'agree' if len(verdicts) <= 1 else 'DISAGREE'}"
        f" | {'UNRESOLVED' if unresolved else 'resolved'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("start", help="fan a review spec out to proposer/adversary/replicator")
    s.add_argument("--topic", required=True, help="short slug for the round directory")
    s.add_argument("--spec", required=True, help="path to the specification file")
    s.add_argument("--rotation", type=int, default=0, help="round index; rotates roles")
    s.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    s.add_argument("--round-dir", default=None, help="override the round directory")
    s.set_defaults(func=start)

    p = sub.add_parser("propose", help="stage one: independent designs")
    p.add_argument("--topic", required=True)
    p.add_argument("--problem", required=True, help="open problem statement, not a spec")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    p.set_defaults(func=propose)

    c = sub.add_parser("critique", help="stage two: everyone attacks every proposal")
    c.add_argument("--round", required=True)
    c.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    c.set_defaults(func=critique)

    d = sub.add_parser("diverge", help="table the disagreement once answers are in")
    d.add_argument("--round", required=True)
    d.set_defaults(func=diverge)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
