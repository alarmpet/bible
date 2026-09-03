from __future__ import annotations
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'native_host' / 'install_native_host.ps1'
TEMPLATE = ROOT / 'native_host' / 'com.nollam.flow_automation.json.template'

def test_manifest_allows_only_selected_extension(tmp_path: Path) -> None:
    launcher = json.dumps(str(ROOT / 'native_host' / 'host_launcher.cmd'))[1:-1]
    text = TEMPLATE.read_text(encoding='utf-8').replace('__HOST_LAUNCHER__', launcher).replace('__EXTENSION_ID__', 'abcdefghijklmnopabcdefghijklmnop')
    rendered = json.loads(text)
    assert rendered['allowed_origins'] == ['chrome-extension://abcdefghijklmnopabcdefghijklmnop/']
    assert Path(rendered['path']).name == 'host_launcher.cmd'

def test_installer_rejects_non_extension_id() -> None:
    result = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(SCRIPT), '-ExtensionId', 'not-an-id'], capture_output=True, text=True)
    assert result.returncode != 0
    assert '32 lowercase letters' in (result.stdout + result.stderr)

def test_whatif_emits_diagnostic_without_manifest_write(tmp_path: Path) -> None:
    result = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(SCRIPT), '-ExtensionId', 'abcdefghijklmnopabcdefghijklmnop', '-WhatIf'], capture_output=True, text=True)
    assert result.returncode == 0
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload['what_if'] is True
    assert payload['registry_path'].startswith('HKCU:')
