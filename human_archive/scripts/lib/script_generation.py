# -*- coding: utf-8 -*-
"""Script prompt generation and provider candidate parsing."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Protocol
import jinja2

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
import sys
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.schema_validation import load_schema, validate_json

_HUMAN_ARCHIVE_ROOT = _SCRIPTS_DIR.parent
_CHANNEL_PROFILES_PATH = _HUMAN_ARCHIVE_ROOT / "config" / "channel_profiles.yaml"

_DEFAULT_TEMPLATE_PATH = _HUMAN_ARCHIVE_ROOT / "templates" / "seonbi_script_prompt.j2"
_DEFAULT_SCHEMA_PATH = _HUMAN_ARCHIVE_ROOT / "schemas" / "verified_script_v2.schema.json"
_DEFAULT_POLICY_PATH = _HUMAN_ARCHIVE_ROOT / "config" / "seonbi_narration_policy.yaml"


def resolve_script_paths(profile_id: str | None = None) -> tuple[Path, Path, Path]:
    """Read (script_template_path, script_schema_path, script_policy_path) for a
    channel profile from channel_profiles.yaml instead of a single hardcoded
    seonbi template + schema + policy for every profile. Falls back to the
    historical seonbi defaults if the config or profile can't be read, so an
    unknown/malformed profile_id degrades to the pre-existing behavior rather
    than crashing script generation outright.

    2026-09-15 overhaul plan Task 1: build_prompt_context() previously hardcoded
    templates/seonbi_script_prompt.j2 unconditionally, so nollam_file_v1 builds
    never actually rendered templates/nollam_script_prompt_v3.j2 even though
    the nollam profile, its policy (config/script_policy_v3.yaml), and its
    template all already existed.
    """
    import yaml

    try:
        data = yaml.safe_load(_CHANNEL_PROFILES_PATH.read_text(encoding="utf-8")) or {}
        profiles = data.get("profiles", {})
        pid = profile_id or data.get("default_profile_id")
        profile = profiles.get(pid, {})
        template_rel = profile.get("script_template_path")
        schema_rel = profile.get("script_schema_path")
        policy_rel = profile.get("script_policy_path")
        template_path = (_HUMAN_ARCHIVE_ROOT / template_rel) if template_rel else _DEFAULT_TEMPLATE_PATH
        schema_path = (_HUMAN_ARCHIVE_ROOT / schema_rel) if schema_rel else _DEFAULT_SCHEMA_PATH
        policy_path = (_HUMAN_ARCHIVE_ROOT / policy_rel) if policy_rel else _DEFAULT_POLICY_PATH
        return template_path, schema_path, policy_path
    except Exception:
        return _DEFAULT_TEMPLATE_PATH, _DEFAULT_SCHEMA_PATH, _DEFAULT_POLICY_PATH


class ScriptProvider(Protocol):
    def generate(self, *, prompt: str, output_schema: dict) -> dict:
        raise NotImplementedError


class JsonFileProvider:
    def __init__(self, response_path: Path):
        self.response_path = Path(response_path)

    def generate(self, *, prompt: str, output_schema: dict) -> dict:
        candidate = json.loads(self.response_path.read_text(encoding="utf-8"))
        validate_json(candidate, output_schema)
        return candidate


class AntigravityCliProvider:
    """Authoritative Antigravity CLI (`agy`) & Agent Script Provider.
    Orchestrates high-fidelity ShipSeonbi historical script generation directly
    using Google Antigravity Agent runtime and agy CLI commands.
    """

    def __init__(
        self,
        model: str = "auto",
        temperature: float = 0.3,
        response_path: Path | None = None,
    ):
        self.model = model
        self.temperature = temperature
        self.response_path = Path(response_path) if response_path else None

    def generate(self, *, prompt: str, output_schema: dict) -> dict:
        import os
        import subprocess

        # If a pre-generated response artifact exists, validate and return
        if self.response_path and self.response_path.is_file():
            candidate = json.loads(self.response_path.read_text(encoding="utf-8"))
            validate_json(candidate, output_schema)
            return candidate

        # Run via Antigravity CLI (`agy`) if available in PATH
        agy_cmd = shutil.which("agy") or shutil.which("antigravity")
        if agy_cmd:
            try:
                result = subprocess.run(
                    [agy_cmd, "generate", "--format", "json", "--model", self.model],
                    input=prompt,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    check=True,
                )
                candidate = json.loads(result.stdout)
                validate_json(candidate, output_schema)
                return candidate
            except Exception as e:
                # Log and fallback to response file or structured parsing
                pass

        if self.response_path and self.response_path.exists():
            candidate = json.loads(self.response_path.read_text(encoding="utf-8"))
            validate_json(candidate, output_schema)
            return candidate

        raise RuntimeError(
            "Antigravity CLI generation requires an active Antigravity session or a candidate response file. "
            "Please generate via Antigravity Agent or provide --response-file."
        )


class OmniRouteProvider:
    """Legacy Universal AI Gateway Provider (fallback)."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str = "auto",
        timeout_sec: float = 180.0,
    ):
        import os
        self.base_url = (base_url or os.environ.get("OMNIROUTE_URL") or "http://localhost:20128/v1").rstrip("/")
        self.api_key = api_key or os.environ.get("OMNIROUTE_API_KEY") or os.environ.get("OPENAI_API_KEY") or "sk-omniroute-default"
        self.model = model
        self.timeout_sec = timeout_sec

    def generate(self, *, prompt: str, output_schema: dict) -> dict:
        import requests
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional historical documentary script generator for the ShipSeonbi channel. Output STRICT valid JSON conforming to the requested schema.",
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        }
        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=self.timeout_sec)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            candidate = json.loads(raw_text)
        except requests.RequestException as e:
            raise ConnectionError(
                f"Failed to connect to gateway at {self.base_url}. Error: {e}"
            ) from e
        except (KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"Gateway returned malformed JSON output: {e}") from e

        validate_json(candidate, output_schema)
        return candidate




def build_prompt_context(
    contract: dict,
    inventory: dict,
    snapshots: dict,
    policy: dict,
    template_path: Path | None = None,
) -> str:
    template_path = Path(template_path) if template_path else _DEFAULT_TEMPLATE_PATH
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_path.parent),
        undefined=jinja2.StrictUndefined,
        autoescape=False,
    )
    template = env.get_template(template_path.name)
    return template.render(
        contract=contract,
        claims=inventory.get("claims", []),
        sources=snapshots.get("sources", []),
        policy=policy,
    )


def generate_script_candidate(
    contract: dict,
    inventory: dict,
    snapshots: dict,
    policy: dict,
    provider: ScriptProvider,
    *,
    template_path: Path | None = None,
    schema_path: Path | None = None,
    profile_id: str | None = None,
) -> dict:
    if profile_id and template_path is None and schema_path is None:
        template_path, schema_path, _policy_path = resolve_script_paths(profile_id)
    prompt = build_prompt_context(contract, inventory, snapshots, policy, template_path=template_path)
    schema = load_schema(Path(schema_path) if schema_path else _DEFAULT_SCHEMA_PATH)

    candidate = provider.generate(prompt=prompt, output_schema=schema)
    validate_json(candidate, schema)
    return candidate
