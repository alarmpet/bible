# -*- coding: utf-8 -*-
"""Sanitize scripture/narration text that triggers angry TTS prosody.

Strips liturgical headers, parenthetical notes (셀라), expression tags,
and softens bangs/questions to periods for calm delivery.
Does not call scripture_tts_prep.soften_for_speech — logic lives here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


BANGS = ["!?", "❗", "！", "!", "？", "?"]
PARENS = re.compile(r"\([^()]*\)|（[^（）]*）")
HEADERS = re.compile(
    r"(다윗의 시|고라 자손의 시|아삽의 시|영장으로|현악|스미닛|마스길|믹담|셀라|Selah)"
)
TAGS = re.compile(r"</?(?:laugh|breath|sigh)>", re.I)

# Residual emotion/prosody triggers that must not reach TTS after sanitize.
_EMOTION_TRIGGER_RE = re.compile(
    r"[!?！？❗]|</?(?:laugh|breath|sigh)>",
    re.I,
)


@dataclass
class SanitizedText:
    original: str
    tts: str
    display: str
    removed: list[str] = field(default_factory=list)


def assert_no_emotion_triggers(text: str) -> None:
    """Raise ValueError if bangs, questions, or expression tags remain."""
    if not text:
        return
    match = _EMOTION_TRIGGER_RE.search(text)
    if match:
        raise ValueError(
            f"emotion/prosody trigger remaining in sanitized text: {match.group()!r}"
        )


def sanitize_script(text: str) -> SanitizedText:
    """Strip headers/selah/tags and soften punctuation for calm TTS.

    Returns SanitizedText with tts and display sharing the cleaned body.
    """
    original = text or ""
    t = PARENS.sub(" ", original)
    t = TAGS.sub(" ", t)
    removed: list[str] = []
    # 괄호 밖 표제/셀라도 제거
    t = HEADERS.sub(" ", t)
    for mark in BANGS:
        t = t.replace(mark, ".")
    t = re.sub(r"[.]{2,}", ".", t)
    t = re.sub(r"\s+\.", ".", t)
    t = re.sub(r"\s+", " ", t).strip()
    assert_no_emotion_triggers(t)
    return SanitizedText(original=original, tts=t, display=t, removed=removed)
