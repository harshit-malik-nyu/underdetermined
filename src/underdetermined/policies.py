"""
Reference interview policies, to bracket the problem.

Each is degenerate in a different direction, which is the point: an agent that
beats all four has done something none of them does, and the gaps between them
show what that something is worth.
"""

from __future__ import annotations

from .determinability import Determinability, Oracle, Verdict, assess
from .interview import Action, Interview, SWEEPABLE, informative_now, step


def run_policy(interview: Interview, policy, oracle: Oracle,
               material_spread: float = 50.0, max_turns: int = 12) -> Interview:
    """Drive an interview to completion under a policy."""
    turns = 0
    while not interview.finished and turns < max_turns:
        action = policy(interview, oracle, material_spread)
        step(interview, action, oracle, material_spread)
        turns += 1
    return interview


def answer_immediately(interview: Interview, oracle, material_spread):
    """
    Never ask. Guess from whatever was volunteered.

    Zero waste, maximal unsafe rate. The naive agent.
    """
    inc = (interview.household.employment_income
           if "employment_income" in interview.known else 18_000)
    return Action.answer(Verdict.ELIGIBLE if inc < 20_000
                         else Verdict.NOT_ELIGIBLE)


def ask_everything(interview: Interview, oracle, material_spread):
    """
    Ask for every field, then answer.

    Zero unsafe rate and maximal waste. Safe in the sense that a form
    demanding forty documents is safe: nothing goes wrong except that people
    give up.
    """
    for f in SWEEPABLE:
        if f not in interview.known and f not in interview.asked:
            return Action.ask(f)
    r = assess(interview.current_case(), oracle, material_spread=material_spread)
    return Action.answer(r.truth)


def abstain_if_anything_unknown(interview: Interview, oracle, material_spread):
    """
    Never ask, abstain unless everything is already known.

    Safe, cheap, and useless on almost every real intake, because claimants
    rarely volunteer everything.
    """
    if interview.unknown():
        return Action.answer(Verdict.CANNOT_DETERMINE)
    r = assess(interview.current_case(), oracle, material_spread=material_spread)
    return Action.answer(r.truth)


def optimal(interview: Interview, oracle, material_spread):
    """
    The ceiling: ask only what is informative, stop the moment the case
    closes.

    Uses the oracle to decide, so it is not implementable by an agent — it
    exists to show what perfect information-seeking costs in questions, which
    is the number an agent should be compared against rather than zero.
    """
    current = assess(interview.current_case(), oracle,
                     material_spread=material_spread)
    if current.label is Determinability.DETERMINABLE:
        return Action.answer(current.truth)

    for f in interview.unknown():
        if informative_now(interview, f, oracle, material_spread):
            return Action.ask(f)

    # Open but nothing left that would close it: abstaining is correct.
    return Action.answer(Verdict.CANNOT_DETERMINE)


POLICIES = {
    "answer immediately": answer_immediately,
    "ask everything": ask_everything,
    "abstain if anything unknown": abstain_if_anything_unknown,
    "optimal (ceiling)": optimal,
}
