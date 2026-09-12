"""Deterministic conversion of legacy two-line ASS events to one-line events."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


_ASS_TIME = re.compile(r"^(?P<h>\d+):(?P<m>\d{2}):(?P<s>\d{2})\.(?P<cs>\d{2})$")


def _to_centiseconds(value: str) -> int:
    match = _ASS_TIME.match(value.strip())
    if not match:
        raise ValueError(f"Invalid ASS timestamp: {value!r}")
    return (
        int(match.group("h")) * 360_000
        + int(match.group("m")) * 6_000
        + int(match.group("s")) * 100
        + int(match.group("cs"))
    )


def _format_centiseconds(value: int) -> str:
    if value < 0:
        raise ValueError("ASS timestamp cannot be negative")
    hours, remainder = divmod(value, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    seconds, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def _replace_event_timing(line: str, start: int, end: int, text: str) -> str:
    fields = line.rstrip("\r\n").split(",", 9)
    if len(fields) != 10:
        raise ValueError(f"Malformed ASS dialogue event: {line!r}")
    fields[1] = _format_centiseconds(start)
    fields[2] = _format_centiseconds(end)
    fields[9] = text
    return ",".join(fields)


def convert_ass_to_one_line(source_path: Path, target_path: Path) -> dict[str, Any]:
    """Split each ``\\N`` event into contiguous one-line events.

    Event timing is represented in ASS centiseconds, so the emitted events are
    contiguous at the format's native precision and cannot overlap.
    """
    source_path = Path(source_path)
    target_path = Path(target_path)
    output: list[str] = []
    dialogue_input = 0
    multiline_input = 0
    dialogue_output = 0

    for raw_line in source_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.startswith("Dialogue:"):
            output.append(raw_line)
            continue
        dialogue_input += 1
        fields = raw_line.split(",", 9)
        if len(fields) != 10:
            raise ValueError(f"Malformed ASS dialogue event: {raw_line!r}")
        start = _to_centiseconds(fields[1])
        end = _to_centiseconds(fields[2])
        if end <= start:
            raise ValueError(f"ASS event has non-positive duration: {raw_line!r}")
        text = fields[9]
        parts = text.split(r"\N")
        if len(parts) == 1:
            output.append(raw_line)
            dialogue_output += 1
            continue

        multiline_input += 1
        span = end - start
        if span < len(parts):
            # A one-centisecond event cannot be split without changing the
            # timeline. Keep it one-line while retaining all visible text.
            output.append(_replace_event_timing(raw_line, start, end, " ".join(parts)))
            dialogue_output += 1
            continue

        lengths = [max(1, len(part.strip())) for part in parts]
        total_length = sum(lengths)
        cursor = start
        remaining_span = span
        remaining_length = total_length
        for index, part in enumerate(parts):
            if index == len(parts) - 1:
                next_cursor = end
            else:
                allocation = max(1, round(remaining_span * lengths[index] / remaining_length))
                allocation = min(allocation, remaining_span - (len(parts) - index - 1))
                next_cursor = cursor + allocation
            output.append(_replace_event_timing(raw_line, cursor, next_cursor, part))
            dialogue_output += 1
            cursor = next_cursor
            remaining_span = end - cursor
            remaining_length -= lengths[index]

    target_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = target_path.with_suffix(target_path.suffix + ".part")
    temporary.write_text("\n".join(output) + "\n", encoding="utf-8", newline="\n")
    with open(temporary, "r+b") as handle:
        os.fsync(handle.fileno())
    os.replace(temporary, target_path)
    return {
        "status": "PASS",
        "dialogue_input": dialogue_input,
        "multiline_input": multiline_input,
        "dialogue_output": dialogue_output,
    }
