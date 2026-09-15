# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import pytest

def test_skill_opening_policy_consistency():
    module_root = Path(r"D:\module")
    flow_skill = module_root / ".agents" / "skills" / "flow-batch-orchestrator" / "SKILL.md"
    cinematic_skill = module_root / ".agents" / "skills" / "cinematic-hybrid-editing-director" / "SKILL.md"
    
    assert flow_skill.exists(), f"Missing flow skill: {flow_skill}"
    assert cinematic_skill.exists(), f"Missing cinematic skill: {cinematic_skill}"
    
    flow_text = flow_skill.read_text(encoding="utf-8")
    cinematic_text = cinematic_skill.read_text(encoding="utf-8")
    
    # 1. flow-batch-orchestrator must NOT contain bare-tip opening
    assert "씬 1번 순수 베어팁" not in flow_text, "Legacy bare-tip opening found in flow skill!"
    assert "3-Cut Visible FLOW Opening" in flow_text, "Visible-First FLOW opening missing in flow skill!"
    
    # 2. cinematic-hybrid-editing-director must mandate Visible-First
    assert "3-Cut Visible FLOW" in cinematic_text
    assert "Beat-Aware Motion" in cinematic_text or "비트 인지형 모션" in cinematic_text
    assert "Gate 8" in cinematic_text
