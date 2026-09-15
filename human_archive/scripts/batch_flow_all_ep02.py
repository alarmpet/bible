# -*- coding: utf-8 -*-
"""Backward-compatible EP02 wrapper for the generic pilot-first Flow batch."""
from __future__ import annotations

import sys

from generate_flow_batch import main


if __name__ == "__main__":
    if not any(flag in sys.argv for flag in ("--pilot", "--all", "--only")):
        sys.argv.append("--pilot")
    main()
