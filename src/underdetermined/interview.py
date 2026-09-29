"""
The agent decides what to ask, not just whether to answer.

What was wrong with the first version
-------------------------------------
`determinability.py` hands the agent a description ending "Not stated:
dependents." That signposts the gap. The agent is asked to *recognise* that a
named field is missing and reason about whether it matters — which is a
classification problem dressed as a decision.

A real intake does not work that way. A claimant says what they think is
relevant. The gap is not labelled; noticing it is part of the job. And the
response to a gap is not abstention — it is **asking**, which costs the
claimant time and patience, and which they may abandon partway through.

So the agentic problem is not "answer or abstain". It is:

    what do I need to know, what do I ask first, and when do I know enough?

That is a sequential information-gathering policy under a budget, and it is
the capability the application actually requires.

Value of information, computed
------------------------------
The same construction that gives determinability gives the value of each
question. For an unknown field, hold everything currently known fixed and
sweep that field across its range:

    the answer moves   →  asking is INFORMATIVE. The case cannot be closed
                          without it.
    the answer is flat →  asking is WASTED. The claimant is being made to
                          fetch a document that cannot change anything.

Wasted questions are not free and are not harmless. In this application each
one is a phone call, a document request, or a form field, and every added step
is a chance the claimant gives up. Abandonment is the dominant failure mode in
benefits intake, so an agent that asks for everything is not being careful —
it is imposing the exact cost the agent was deployed to remove.

Order matters, and that is the hard part
----------------------------------------
Informativeness is conditional on what is already known. A field that cannot
change the answer today may become decisive once another is learned, and vice
versa. So the agent cannot compute a static list of things to ask; it has to
re-evaluate after every answer.

That is what makes this a trajectory rather than a classification, and it is
why the failures here look like agent failures: asking in a useless order,
asking for something already implied, looping, or stopping while the answer is
still open.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .determinability import (
    SWEEPABLE, Case, Determinability, Household, Oracle, Verdict, assess,
)


class Move(str, Enum):
    ASK = "ask"
    ANSWER = "answer"


@dataclass(frozen=True)
class Action:
    """One agent turn: request a field, or commit to a verdict."""

    move: Move
    field_name: str | None = None
    verdict: Verdict | None = None

    @staticmethod
    def ask(name: str) -> "Action":
        return Action(Move.ASK, field_name=name)

    @staticmethod
    def answer(v: Verdict) -> "Action":
        return Action(Move.ANSWER, verdict=v)


@dataclass
class Turn:
    """A record of what happened, for trajectory scoring."""

    action: Action
    informative: bool | None = None
    """For ASK: would this field's value change the answer, given what is
    already known? None for ANSWER."""
    repeated: bool = False
    invalid: bool = False


@dataclass
class Interview:
    """
    A case presented as an intake conversation.

    The agent starts with whatever the claimant volunteered and may ask for
    more, up to a budget. Nothing tells it which fields exist but are missing
    — `unknown()` is available to the environment for scoring, not to the
    agent.
    """

    household: Household
    known: set[str]
    budget: int = 4
    year: int = 2025

    asked: list[str] = field(default_factory=list)
    turns: list[Turn] = field(default_factory=list)
    finished: bool = False
    final: Verdict | None = None

    def unknown(self) -> tuple[str, ...]:
        return tuple(f for f in SWEEPABLE if f not in self.known)

    def questions_used(self) -> int:
        return sum(1 for t in self.turns if t.action.move is Move.ASK)

    def budget_left(self) -> int:
        return max(0, self.budget - self.questions_used())

    def describe(self) -> str:
        """
        What the claimant has said so far.

        Deliberately does NOT enumerate what is missing. A real intake gives
        you what someone thought to mention; noticing the gap is the agent's
        job, and naming it would hand over the hard half of the problem.
        """
        hh, parts = self.household, []
        if "employment_income" in self.known:
            parts.append(f"earns ${hh.employment_income:,.0f} a year")
        if "dependents" in self.known:
            n = hh.dependents
            parts.append("has no children" if n == 0
                         else f"has {n} child{'ren' if n > 1 else ''}")
        if "age" in self.known:
            parts.append(f"is {hh.age}")
        if "state_name" in self.known:
            parts.append(f"lives in {hh.state_name}")
        if not parts:
            return "A single adult is applying for food assistance."
        return ("A single adult applying for food assistance "
                + ", ".join(parts) + ".")

    def current_case(self) -> Case:
        return Case(self.household, self.unknown(), self.year)


def informative_now(interview: Interview, name: str, oracle: Oracle,
                    material_spread: float = 50.0) -> bool:
    """
    Would learning this field change the answer, given what is known?

    Conditional on current knowledge, which is the whole point: a field can be
    worthless now and decisive two turns later.
    """
    if name in interview.known:
        return False

    others = tuple(f for f in interview.unknown() if f != name)

    # Compare the case as it stands against the case with this field resolved.
    before = assess(Case(interview.household, interview.unknown(),
                         interview.year), oracle,
                    material_spread=material_spread)
    after = assess(Case(interview.household, others, interview.year), oracle,
                   material_spread=material_spread)

    # Asking is informative when it closes an open case, or when it collapses
    # a materially wide range even if the case stays open.
    if before.label is Determinability.DETERMINABLE:
        return False
    if after.label is Determinability.DETERMINABLE:
        return True
    return (before.spread - after.spread) > material_spread


def step(interview: Interview, action: Action, oracle: Oracle,
         material_spread: float = 50.0) -> Turn:
    """Apply one agent action and record what it was worth."""
    if interview.finished:
        raise RuntimeError("interview is already finished")

    if action.move is Move.ANSWER:
        interview.finished = True
        interview.final = action.verdict
        turn = Turn(action=action)
        interview.turns.append(turn)
        return turn

    name = action.field_name
    invalid = name not in SWEEPABLE
    repeated = (name in interview.known) or (name in interview.asked)

    turn = Turn(action=action, repeated=repeated, invalid=invalid)

    if not invalid and not repeated:
        turn.informative = informative_now(interview, name, oracle,
                                           material_spread)
        interview.known.add(name)
        interview.asked.append(name)
    else:
        turn.informative = False

    interview.turns.append(turn)

    # Running out of budget without answering is itself a failure, recorded
    # as an unanswered interview rather than silently forgiven.
    if interview.budget_left() <= 0:
        interview.finished = True
    return turn


def make_interview(household: Household, volunteered: set[str] | None = None,
                   budget: int = 4, year: int = 2025) -> Interview:
    """
    Build an intake where the claimant has volunteered some fields.

    Default is income only, which is what people lead with when applying for
    food assistance and rarely enough to decide.
    """
    return Interview(household=household,
                     known=set(volunteered or {"employment_income"}),
                     budget=budget, year=year)
