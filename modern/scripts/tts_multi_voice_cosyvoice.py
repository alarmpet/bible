# -*- coding: utf-8 -*-
"""Opt-in CosyVoice3 TTS entry. Production default remains SuperTonic3.

    python modern/scripts/tts_multi_voice_cosyvoice.py --job <job> --preview-only
    python modern/scripts/tts_multi_voice.py --job <job> --engine cosyvoice3 --preview-only
"""
from __future__ import annotations

import sys

from tts_multi_voice import main as _tts_main


def main() -> None:
    if "--engine" not in sys.argv:
        sys.argv[1:1] = ["--engine", "cosyvoice3"]
    _tts_main()


if __name__ == "__main__":
    main()
