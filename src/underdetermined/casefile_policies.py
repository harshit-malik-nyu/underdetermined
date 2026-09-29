"""
Reference policies for the unreliable environment.

Each is degenerate in a way the clean interview could not express, which is
the point of building this layer.
"""

from __future__ import annotations

from .casefile import CaseFile
from .determinability import Verdict
from .sources import SOURCES, Outcome


def _guess(cf: CaseFile) -> Verdict:
    """Decide from whatever is believed, however it got there."""
    inc = cf.believed.get("employment_income")
    dep = cf.believed.get("dependents", 0)
    if inc is None:
        return Verdict.CANNOT_DETERMINE
    return Verdict.ELIGIBLE if inc < 15_000 + 9_000 * dep else Verdict.NOT_ELIGIBLE


def close_immediately(cf: CaseFile) -> None:
    """Decide from nothing. Maximal unsafe, zero requests."""
    cf.close(Verdict.CANNOT_DETERMINE if not cf.believed else _guess(cf))


def self_report_only(cf: CaseFile) -> None:
    """
    Ask the applicant and believe them.

    Always available, never precise, sometimes stale. The policy a fast agent
    falls into, and it trusts figures it was told were months old.
    """
    cf.ask("self_report")
    cf.close(_guess(cf))


def exhaust_everything(cf: CaseFile) -> None:
    """
    Request every source until the budget runs out.

    Safe in the sense that a form demanding forty documents is safe. It also
    retries documents it has been told are unreadable, which is the specific
    waste this environment can see and the clean one cannot.
    """
    # Reserve the last turn to decide. Spending the entire budget gathering
    # and never closing is a stall, and the first version of this policy did
    # exactly that on every case — which looked like 0% accuracy rather than
    # the failure it was.
    while cf.budget_left() > 1:
        for name in SOURCES:
            if cf.budget_left() <= 1:
                break
            cf.ask(name)
    if not cf.finished:
        cf.close(_guess(cf))


def one_shot_each(cf: CaseFile) -> None:
    """
    Try each source once and give up on anything that fails.

    Cheap and it abandons sources that would have arrived on a retry — the
    opposite error to exhausting, and more expensive for the applicant
    because the case goes unresolved.
    """
    for name in SOURCES:
        if cf.budget_left() <= 0:
            break
        if len(cf.unknown()) == 0:
            break
        cf.ask(name)
    if not cf.finished:
        cf.close(_guess(cf))


def sensible(cf: CaseFile) -> None:
    """
    The behaviour the environment rewards, hand-written.

    Retry what can be retried, never re-request an unreadable document, seek
    confirmation when a source contradicts or flags itself stale, and stop
    once the remaining unknowns cannot change the answer.

    It is not optimal and is not meant to be — it is the bar an agent should
    clear, written out so the gap to it is legible.
    """
    illegible: set[str] = set()
    stale_fields: set[str] = set()
    clashed: set[str] = set()

    def try_source(name: str, retries: int = 1) -> None:
        for _ in range(retries + 1):
            if cf.budget_left() <= 0 or name in illegible:
                return
            r = cf.ask(name)
            if r.outcome is Outcome.ILLEGIBLE:
                illegible.add(name)
                return
            if r.outcome is Outcome.STALE:
                stale_fields.update(r.revealed)
            if r.contradicts:
                clashed.update(r.contradicts)
            if r.outcome in (Outcome.ARRIVED, Outcome.STALE):
                return

    try_source("self_report")
    if "employment_income" in stale_fields or cf.believed.get("employment_income") is None:
        try_source("pay_stub", retries=1)
    if clashed and cf.budget_left() > 0:
        try_source("agency_letter", retries=1)
    if "age" in cf.unknown() and cf.budget_left() > 0:
        try_source("id_document")

    if not cf.finished:
        cf.close(_guess(cf))


POLICIES = {
    "close immediately": close_immediately,
    "self-report only": self_report_only,
    "exhaust everything": exhaust_everything,
    "one shot each": one_shot_each,
    "sensible (hand-written)": sensible,
}
