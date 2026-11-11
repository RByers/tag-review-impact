"""Headless, sandboxed Claude calls on untrusted text (SECURITY.md).

Every model call that sees issue or comment text goes through `ask()`:
  - `claude -p` with no tools, no MCP servers, no slash commands or skills,
    no session persistence and a replaced system prompt;
  - output forced to a JSON schema (`--json-schema`), and the caller keeps
    only the fields and ids it expects;
  - run by tagimpact.sandbox.Sandbox: scrubbed env, fresh HOME, bwrap jail
    hiding /home (this repo, ~/.claude, ~/.ssh, ~/.secrets) and /run/user.
"""

import json
import re
import time

from .sandbox import Sandbox

MODELS = {"haiku": "haiku", "fable": "claude-fable-5-1", "sonnet": "sonnet", "opus": "opus"}


def make_sandbox(mode="bwrap"):
    from .paths import PRIVATE, ROOT
    return Sandbox(mode=mode, hide=[ROOT, PRIVATE])


def ask(sandbox, model, system, prompt, schema, timeout_retries=2):
    """One schema-constrained call. Returns (structured_output dict, cost dict)."""
    args = ["-p", "--model", MODELS.get(model, model), "--output-format", "json", "--tools", "",
            "--system-prompt", system,
            "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--disable-slash-commands",
            "--exclude-dynamic-system-prompt-sections", "--no-session-persistence",
            "--json-schema", json.dumps(schema)]
    last = None
    for attempt in range(timeout_retries + 1):
        t0 = time.time()
        p = sandbox.run(args, prompt)
        wall = time.time() - t0
        try:
            d = json.loads(p.stdout)
        except ValueError:
            last = RuntimeError(f"claude -p failed (exit {p.returncode}): {(p.stderr or p.stdout)[:400]}")
            time.sleep(10 * (attempt + 1))
            continue
        if d.get("is_error"):
            last = RuntimeError(f"claude -p error: {str(d.get('result'))[:400]}")
            time.sleep(10 * (attempt + 1))
            continue
        out = d.get("structured_output")
        if not out:
            m = re.search(r"\{.*\}", d.get("result") or "", re.S)
            try:
                out = json.loads(m.group(0)) if m else None
            except ValueError:
                out = None
        if not isinstance(out, dict):
            last = RuntimeError("no structured output")
            continue
        u = d.get("usage", {})
        return out, {"wall": round(wall, 1), "usd": d.get("total_cost_usd") or 0,
                     "model": sorted(d.get("modelUsage", {}) or {model: 1})[0],
                     "tokens": sum(u.get(k, 0) or 0 for k in ("input_tokens", "cache_creation_input_tokens",
                                                               "cache_read_input_tokens", "output_tokens"))}
    raise last


_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f​-‏‪-‮⁦-⁩]")
_URL = re.compile(r"(?:https?|javascript|data):\S*", re.I)
_MARKUP = re.compile(r"[<>`\[\]{}]")


def clean_text(s, limit):
    """Model-written text reduced to plain words: no URLs, markup or control
    characters, at most `limit` characters. It is still shown only as text."""
    s = _CTRL.sub("", str(s or ""))
    s = _URL.sub("", s)
    s = _MARKUP.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]
