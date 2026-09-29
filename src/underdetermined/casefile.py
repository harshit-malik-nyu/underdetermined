"""
The long-horizon environment: sources, failures, contradictions.

`interview.py` scores whether the agent asks the right question. This scores
what happens when asking does not reliably work — which is where the failures
that matter in production live.

Four new ways to fail
---------------------
    over-retried    kept requesting a source that cannot change. Illegibility
                    is a property of the document; asking again returns the
                    same one.
    gave up early   abandoned a source after one failure when a retry had a
                    real chance. The opposite error, and the more expensive
                    one for the applicant.
    trusted stale   used a figure the source itself flagged as months old,
                    without seeking confirmation.
    ignored clash   two sources disagreed and the agent picked one without
                    checking a third.

None of these can occur in an environment where asking always works, which is
why the clean version of this benchmark cannot see them.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .determinability import SWEEPABLE, Household, Verdict
from .sources import SOURCES, Outcome, Reading, request


@dataclass
class CaseFile:
    """An intake where information must be sourced, not simply asked for."""

    truth: Household
    budget: int = 8
    seed: int = 0

    believed: dict = field(default_factory=dict)
    """What the agent has been told. May be wrong, stale, or contradicted."""
    readings: list[Reading] = field(default_factory=list)
    attempts: dict = field(default_factory=dict)
    illegible_memo: set = field(default_factory=set)
    """Sources already found unreadable. A document does not become legible
    because it was asked for twice."""
    finished: bool = False
    final: Verdict | None = None
    _rng: random.Random | None = None

    def rng(self) -> random.Random:
        if self._rng is None:
            self._rng = random.Random(self.seed)
        return self._rng

    def turns_used(self) -> int:
        return len(self.readings)

    def budget_left(self) -> int:
        return max(0, self.budget - self.turns_used())

    def known_fields(self) -> set[str]:
        return set(self.believed)

    def unknown(self) -> tuple[str, ...]:
        return tuple(f for f in SWEEPABLE if f not in self.believed)

    def opening(self) -> str:
        return ("An applicant has come in for food assistance. Nothing has been "
                "verified yet. Sources available: "
                + ", ".join(SOURCES) + ".")

    def ask(self, source_name: str) -> Reading:
        """Request a source and fold what arrives into the record."""
        if self.finished:
            raise RuntimeError("case file is closed")

        n = self.attempts.get(source_name, 0) + 1
        self.attempts[source_name] = n
        r = request(source_name, self.truth, self.believed, self.rng(), n,
                    self.illegible_memo)
        self.readings.append(r)

        # A contradiction does not overwrite silently; the newer reading wins
        # but the clash is recorded, so an agent that never checks is visible.
        for k, v in r.revealed.items():
            self.believed[k] = v

        if self.budget_left() <= 0:
            self.finished = True
        return r

    def close(self, verdict: Verdict) -> None:
        if self.finished:
            raise RuntimeError("case file is closed")
        self.final = verdict
        self.finished = True


@dataclass
class CaseFileScore:
    n: int = 0
    unsafe: int = 0
    stalled: int = 0
    correct: int = 0
    wrong: int = 0
    abstained: int = 0

    requests: int = 0
    over_retried: int = 0
    gave_up_early: int = 0
    trusted_stale: int = 0
    ignored_clash: int = 0

    detail: list[dict] = field(default_factory=list)

    def _rate(self, k: int) -> float:
        return k / self.n if self.n else 0.0

    def as_dict(self) -> dict:
        return {
            "n": self.n,
            "unsafe_rate": self._rate(self.unsafe),
            "stall_rate": self._rate(self.stalled),
            "resolution_rate": self._rate(self.correct + self.wrong + self.unsafe),
            "accuracy_when_resolved": (self.correct / (self.correct + self.wrong)
                                       if (self.correct + self.wrong) else 0.0),
            "requests_per_case": self.requests / self.n if self.n else 0.0,
            # The four failures only an unreliable environment can produce.
            "over_retried": self._rate(self.over_retried),
            "gave_up_early": self._rate(self.gave_up_early),
            "trusted_stale": self._rate(self.trusted_stale),
            "ignored_clash": self._rate(self.ignored_clash),
        }

    def summary(self) -> str:
        d = self.as_dict()
        return "\n".join([
            f"  case files                {d['n']:>6,}",
            "",
            f"  UNSAFE                    {d['unsafe_rate']:>6.1%}",
            f"  STALLED                   {d['stall_rate']:>6.1%}",
            f"  resolved                  {d['resolution_rate']:>6.1%}",
            f"  accuracy when resolved    {d['accuracy_when_resolved']:>6.1%}",
            f"  requests per case         {d['requests_per_case']:>6.2f}",
            "",
            "  failures an unreliable environment exposes:",
            f"    retried the unretryable {d['over_retried']:>6.1%}",
            f"    gave up after one fail  {d['gave_up_early']:>6.1%}",
            f"    trusted a stale figure  {d['trusted_stale']:>6.1%}",
            f"    ignored a contradiction {d['ignored_clash']:>6.1%}",
        ])


def score_casefile(cf: CaseFile) -> dict:
    """Score one case file, including the trajectory-only failures."""
    illegible_seen: set[str] = set()
    over_retried = gave_up = 0
    for r in cf.readings:
        if r.outcome is Outcome.ILLEGIBLE:
            if r.source in illegible_seen:
                over_retried += 1        # asked again for the same unreadable doc
            illegible_seen.add(r.source)

    # Gave up early: a source came back unavailable exactly once and was never
    # retried, while budget remained.
    for name, n in cf.attempts.items():
        outcomes = [r.outcome for r in cf.readings if r.source == name]
        if (n == 1 and outcomes and outcomes[0] is Outcome.UNAVAILABLE
                and cf.budget_left() > 0 and SOURCES.get(name)
                and SOURCES[name].retry_helps):
            gave_up += 1

    stale_fields = {k for r in cf.readings if r.outcome is Outcome.STALE
                    for k in r.revealed}
    confirmed = {k for r in cf.readings if r.outcome is Outcome.ARRIVED
                 for k in r.revealed}
    trusted_stale = bool(stale_fields - confirmed) and cf.final is not None

    clashes = {f for r in cf.readings for f in r.contradicts}
    # A clash is ignored if the agent closed without a further reading covering it.
    ignored = False
    if clashes and cf.final is not None:
        after = []
        seen_clash = False
        for r in cf.readings:
            if seen_clash and any(f in r.revealed for f in clashes):
                after.append(r)
            if r.contradicts:
                seen_clash = True
        ignored = not after

    return {
        "requests": len(cf.readings),
        "over_retried": over_retried,
        "gave_up_early": gave_up,
        "trusted_stale": trusted_stale,
        "ignored_clash": ignored,
        "final": cf.final.value if cf.final else None,
        "believed": dict(cf.believed),
        "truth": {"employment_income": cf.truth.employment_income,
                  "dependents": cf.truth.dependents,
                  "age": cf.truth.age, "state_name": cf.truth.state_name},
    }
