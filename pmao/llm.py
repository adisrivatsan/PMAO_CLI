import json
import shutil
import subprocess
from typing import Any


class LLMError(Exception):
    pass


def detect_backend(config_override: str = None) -> str:
    if config_override:
        return config_override
    if shutil.which("claude"):
        return "claude"
    if shutil.which("codex"):
        return "codex"
    raise LLMError(
        "No LLM backend found. Install Claude Code (claude) or OpenAI Codex CLI (codex)."
    )


def _run(backend: str, prompt: str, timeout: int = 120) -> str:
    if backend == "claude":
        cmd = ["claude", "-p", prompt]
    else:
        cmd = ["codex", "-q", prompt]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise LLMError(f"Backend timed out after {timeout}s")
    if result.returncode != 0:
        raise LLMError(
            f"Backend '{backend}' exited {result.returncode}.\nstderr: {result.stderr.strip()[:500]}"
        )
    return result.stdout.strip()


def call_text(prompt: str, config_override: str = None, timeout: int = 120) -> str:
    """Call the LLM and return raw text output (for status, summarize)."""
    backend = detect_backend(config_override)
    return _run(backend, prompt, timeout)


def call_structured(
    prompt: str,
    config_override: str = None,
    timeout: int = 120,
) -> Any:
    """Call the LLM and return parsed JSON (for ingest, update)."""
    backend = detect_backend(config_override)
    for attempt in range(2):
        current_prompt = prompt
        if attempt == 1:
            current_prompt += "\n\nIMPORTANT: Respond ONLY with valid JSON. No preamble, no explanation, no markdown."
        raw = _run(backend, current_prompt, timeout)
        text = raw
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(l for l in lines if not l.startswith("```")).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            if attempt == 1:
                raise LLMError(
                    f"LLM returned unparseable JSON after 2 attempts.\nRaw output:\n{raw[:500]}"
                )
