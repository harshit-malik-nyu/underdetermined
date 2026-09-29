"""
A real model conducting the interview.

The agent sees only what the claimant has said. It is not told which fields
exist but are missing — that is the half of the problem the first version of
this benchmark gave away.

Each turn it either requests one piece of information or commits to a verdict.
The prompt names the available fields (an agent cannot ask for something it
does not know exists) and states the budget, and says nothing else. No
examples, no instruction to reason first, no nudge toward caution. A benchmark
whose result moves with prompt tinkering measures the prompt.
"""

from __future__ import annotations

import json
import os
import re

from .agent import AgentConfig
from .determinability import SWEEPABLE, Verdict
from .interview import Action, Interview

SYSTEM = """You are taking an intake for SNAP (US food assistance) eligibility.

Each turn, reply with exactly one line:

  ASK <field>   - request one piece of information
  ANSWER ELIGIBLE | NOT_ELIGIBLE | CANNOT_DETERMINE

Fields you may ask for: employment_income, dependents, age, state_name.

Asking costs the applicant time, and applicants abandon long intakes. Ask only
for what could change your answer. Answer as soon as you can decide."""


def parse_action(text: str) -> Action:
    """
    Map a reply to an action.

    An unparseable reply becomes CANNOT_DETERMINE rather than being retried or
    dropped. Retrying would hide a malformed-output failure; dropping would
    remove the agent's worst turns from the denominator.
    """
    t = text.strip().upper()
    m = re.search(r"\bASK\s+([A-Z_]+)", t)
    if m:
        name = m.group(1).lower()
        return Action.ask(name if name in SWEEPABLE else name)
    if "CANNOT" in t or "UNDETERMIN" in t:
        return Action.answer(Verdict.CANNOT_DETERMINE)
    if re.search(r"\bNOT[_ ]?ELIGIBLE\b", t):
        return Action.answer(Verdict.NOT_ELIGIBLE)
    if "ELIGIBLE" in t:
        return Action.answer(Verdict.ELIGIBLE)
    return Action.answer(Verdict.CANNOT_DETERMINE)


def _call(messages: list[dict], cfg: AgentConfig) -> str:
    key = os.environ.get(cfg.api_key_env)
    if not key:
        raise RuntimeError(
            f"{cfg.api_key_env} is not set. This harness calls a real model; "
            "it does not simulate one.")
    import urllib.request
    body = json.dumps({
        "model": cfg.model, "max_tokens": 32, "temperature": 0.0,
        "system": SYSTEM, "messages": messages,
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"content-type": "application/json", "x-api-key": key,
                 "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    return "".join(b.get("text", "") for b in data.get("content", []))


def agent_policy(cfg: AgentConfig | None = None):
    """A policy backed by a real model, usable wherever a reference policy is."""
    cfg = cfg or AgentConfig()

    def policy(interview: Interview, oracle, material_spread):
        lines = [interview.describe()]
        for t in interview.turns:
            if t.action.field_name:
                name = t.action.field_name
                value = getattr(interview.household, name, None)
                lines.append(f"You asked for {name}. Answer: {value}.")
        lines.append(f"You may ask {interview.budget_left()} more question(s).")
        try:
            reply = _call([{"role": "user", "content": "\n".join(lines)}], cfg)
        except Exception as exc:                       # noqa: BLE001
            print(f"  call failed: {type(exc).__name__}", flush=True)
            return Action.answer(Verdict.CANNOT_DETERMINE)
        return parse_action(reply)

    return policy
