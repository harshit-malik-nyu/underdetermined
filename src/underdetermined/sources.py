"""
Information that arrives unreliably, as it does in real intake.

What the interview benchmark still assumed
------------------------------------------
`interview.py` lets the agent ask for a field and receive the truth. That is a
clean environment, and clean environments hide the failures that matter in
production: an agent that trusts a stale document, retries a source that will
never respond, gives up after one failure, or never notices that two sources
disagree.

None of those can occur when asking always works.

What changes here
-----------------
The agent no longer asks for `employment_income`. It requests a **source** —
a pay stub, a benefits letter, the applicant's own recollection — and a source:

    may not arrive          the employer has not responded, the applicant
                            cannot find it
    may be unreadable       a photographed document, partially legible
    may be stale            accurate as of six months ago, and circumstances
                            changed
    may disagree            the applicant remembers one number, the stub says
                            another

So a single request no longer resolves a field. The agent has to decide which
source to try, whether a failure is worth retrying, when a partial reading is
enough, and what to do when two sources conflict.

Why this is not just noise
--------------------------
Each source has a different profile, and the profiles interact with the case.
Self-report is instant and always available but imprecise; a pay stub is exact
but often missing; an agency letter is authoritative and slow. An agent that
treats them interchangeably will either burn turns on a source that will not
come or trust a number it should have checked.

**The oracle construction survives all of this.** Determinability still means
sweeping the values a field could take — the sweep now runs over what the
agent could still *learn*, given which sources have failed.

On randomness
-------------
Failures are drawn from a fixed seed per case, so a trajectory is reproducible
and two agents face identical conditions. An agent is never punished for bad
luck another agent did not face, which would make the comparison meaningless
at this sample size.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum


class Outcome(str, Enum):
    ARRIVED = "arrived"
    UNAVAILABLE = "unavailable"
    """The source did not respond. Retrying may work."""
    ILLEGIBLE = "illegible"
    """It arrived and could not be read. Retrying the same source will not
    help; another source might."""
    STALE = "stale"
    """It arrived and describes an earlier state of the world."""


@dataclass(frozen=True)
class Source:
    """
    Somewhere information can come from.

    `reveals` is what it covers. `failure` is the chance it does not arrive at
    all, `illegible` the chance it arrives unreadable, `stale` the chance it is
    out of date. `precision` is how exactly it pins a value down: self-report
    gives a band, a pay stub gives a number.
    """

    name: str
    reveals: tuple[str, ...]
    failure: float = 0.0
    illegible: float = 0.0
    stale: float = 0.0
    precision: float = 1.0
    retry_helps: bool = True
    """Whether asking again has any chance of a different result. False for
    illegibility, which is a property of the document."""


SOURCES: dict[str, Source] = {
    # Always there, never precise, and PARTIAL.
    #
    # It originally revealed all four fields, which made every other source
    # redundant — one request ended the interview and there was no
    # information-gathering problem left to study. An applicant volunteers
    # what they carry in their head: roughly what they earn and how many
    # children they have. Age and state come off a document.
    "self_report": Source(
        "self_report", ("employment_income", "dependents"),
        failure=0.0, illegible=0.0, stale=0.15, precision=0.6),

    # Exact and often missing.
    "pay_stub": Source(
        "pay_stub", ("employment_income",),
        failure=0.35, illegible=0.20, stale=0.10, precision=1.0),

    # Authoritative, slow, and worth waiting for.
    "agency_letter": Source(
        "agency_letter", ("dependents", "state_name"),
        failure=0.45, illegible=0.05, stale=0.05, precision=1.0),

    # Cheap, reliable, narrow.
    "id_document": Source(
        "id_document", ("age", "state_name"),
        failure=0.10, illegible=0.15, stale=0.02, precision=1.0),
}


@dataclass
class Reading:
    """What came back from one request."""

    source: str
    outcome: Outcome
    revealed: dict[str, object] = field(default_factory=dict)
    """Fields resolved. Empty unless the outcome is ARRIVED."""
    approximate: bool = False
    """True when the source gives a band rather than a value."""
    contradicts: tuple[str, ...] = ()
    """Fields where this reading disagrees with something already believed."""

    def describe(self) -> str:
        if self.outcome is Outcome.UNAVAILABLE:
            return (f"The {self.source.replace('_',' ')} has not come through. "
                    "It may arrive if requested again.")
        if self.outcome is Outcome.ILLEGIBLE:
            return (f"The {self.source.replace('_',' ')} arrived but cannot be "
                    "read. Requesting it again will return the same document.")
        parts = []
        for k, v in self.revealed.items():
            label = k.replace("_", " ")
            if self.approximate and k == "employment_income":
                lo, hi = int(v * 0.75), int(v * 1.25)
                parts.append(f"{label} is somewhere between ${lo:,} and ${hi:,}")
            else:
                parts.append(f"{label} is {v}")
        body = f"The {self.source.replace('_',' ')} says " + ", ".join(parts) + "."
        if self.outcome is Outcome.STALE:
            body += " It is dated some months ago."
        if self.contradicts:
            body += (" This disagrees with what you were told earlier about "
                     + ", ".join(c.replace("_", " ") for c in self.contradicts) + ".")
        return body


def request(source_name: str, truth, believed: dict, rng: random.Random,
            attempt: int = 1, illegible_memo: set | None = None) -> Reading:
    """
    Request a source and see what comes back.

    `attempt` matters: an unavailable source may arrive on a retry, an
    illegible one never will. An agent that cannot tell those apart will waste
    turns, and that is one of the failures this environment exists to expose.

    Illegibility is MEMOISED per source, which is a correctness fix rather
    than an optimisation. Drawing it fresh each time meant a document declared
    unreadable could become readable on retry — while the message told the
    agent it could not. The environment was rewarding behaviour the metric
    punished, which makes the metric meaningless.
    """
    if source_name not in SOURCES:
        return Reading(source=source_name, outcome=Outcome.UNAVAILABLE)

    src = SOURCES[source_name]
    memo = illegible_memo if illegible_memo is not None else set()

    if source_name in memo:
        return Reading(source=src.name, outcome=Outcome.ILLEGIBLE)
    if attempt == 1 and rng.random() < src.illegible:
        memo.add(source_name)
        return Reading(source=src.name, outcome=Outcome.ILLEGIBLE)

    # Retries improve the odds on availability but never reach certainty.
    fail = src.failure / (1 + 0.6 * (attempt - 1)) if src.retry_helps else src.failure
    if rng.random() < fail:
        return Reading(source=src.name, outcome=Outcome.UNAVAILABLE)

    stale = rng.random() < src.stale
    revealed, contradicts = {}, []
    for f in src.reveals:
        value = getattr(truth, f)
        if stale and f == "employment_income":
            # A stale income figure describes an earlier job.
            value = max(0, int(value * rng.choice([0.6, 0.8, 1.3])))
        revealed[f] = value
        if f in believed and believed[f] != value:
            contradicts.append(f)

    return Reading(
        source=src.name,
        outcome=Outcome.STALE if stale else Outcome.ARRIVED,
        revealed=revealed,
        approximate=src.precision < 1.0,
        contradicts=tuple(contradicts),
    )
