"""
Scoring a trajectory, not a verdict.

Three things can go wrong in an interview and they are different failures:

    answered while still open   UNSAFE. The verdict is a guess and downstream
                                it becomes a filed claim.
    asked a useless question    WASTED. The claimant fetches a document that
                                could not have changed anything. Each one is
                                a chance they abandon the process, which is
                                the dominant failure mode in benefits intake.
    ran out of budget           STALLED. No answer at all, having spent the
                                claimant's patience getting nowhere.

An agent optimising any one of these alone is easy to build and useless.
Asking everything eliminates unsafe answers and maximises waste. Answering
immediately eliminates waste and maximises unsafe answers. The policy has to
trade them, which is why all three are reported together and no summary here
returns one without the others.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .determinability import Determinability, Oracle, Verdict, assess
from .interview import Interview, Move


@dataclass
class TrajectoryScore:
    n: int = 0

    unsafe: int = 0
    """Answered while the case was still underdetermined."""
    stalled: int = 0
    """Budget exhausted without an answer."""
    resolved_correct: int = 0
    resolved_wrong: int = 0
    abstained: int = 0

    questions_asked: int = 0
    questions_wasted: int = 0
    questions_repeated: int = 0
    questions_invalid: int = 0

    detail: list[dict] = field(default_factory=list)

    @property
    def unsafe_rate(self) -> float:
        return self.unsafe / self.n if self.n else 0.0

    @property
    def stall_rate(self) -> float:
        return self.stalled / self.n if self.n else 0.0

    @property
    def waste_rate(self) -> float:
        """Share of questions that could not have changed the answer."""
        if not self.questions_asked:
            return 0.0
        return self.questions_wasted / self.questions_asked

    @property
    def resolution_rate(self) -> float:
        """Share of cases closed with a verdict, correct or not."""
        if not self.n:
            return 0.0
        return (self.resolved_correct + self.resolved_wrong + self.unsafe) / self.n

    @property
    def questions_per_case(self) -> float:
        return self.questions_asked / self.n if self.n else 0.0

    @property
    def asks_everything(self) -> bool:
        return self.waste_rate > 0.5

    def as_dict(self) -> dict:
        return {
            "n": self.n,
            # The three failure modes are always adjacent: any one alone
            # recommends a degenerate policy.
            "unsafe_rate": self.unsafe_rate,
            "waste_rate": self.waste_rate,
            "stall_rate": self.stall_rate,
            "resolution_rate": self.resolution_rate,
            "questions_per_case": self.questions_per_case,
            "accuracy_when_resolved": (
                self.resolved_correct
                / (self.resolved_correct + self.resolved_wrong)
                if (self.resolved_correct + self.resolved_wrong) else 0.0),
            "repeated_questions": self.questions_repeated,
            "invalid_questions": self.questions_invalid,
            "asks_everything": self.asks_everything,
        }

    def summary(self) -> str:
        d = self.as_dict()
        lines = [
            f"  interviews                {d['n']:>6,}",
            "",
            f"  UNSAFE  answered too soon {d['unsafe_rate']:>6.1%}",
            f"  WASTED  useless questions {d['waste_rate']:>6.1%}",
            f"  STALLED out of budget     {d['stall_rate']:>6.1%}",
            "",
            f"  resolved                  {d['resolution_rate']:>6.1%}",
            f"  questions per case        {d['questions_per_case']:>6.2f}",
            f"  accuracy when resolved    {d['accuracy_when_resolved']:>6.1%}",
        ]
        if d["repeated_questions"] or d["invalid_questions"]:
            lines.append(f"  malformed turns           "
                         f"{d['repeated_questions'] + d['invalid_questions']:>6,}")
        if d["asks_everything"]:
            lines += ["", "  Most of this agent's questions could not change the",
                      "  answer. It is buying safety with the claimant's time."]
        return "\n".join(lines)


def score_interview(interview: Interview, oracle: Oracle,
                    material_spread: float = 50.0) -> dict:
    """Score one completed interview."""
    final_case = interview.current_case()
    truth = assess(final_case, oracle, material_spread=material_spread)
    still_open = truth.label is Determinability.UNDERDETERMINED

    asked = [t for t in interview.turns if t.action.move is Move.ASK]
    record = {
        "questions": len(asked),
        "wasted": sum(1 for t in asked if t.informative is False and not t.repeated
                      and not t.invalid),
        "repeated": sum(1 for t in asked if t.repeated),
        "invalid": sum(1 for t in asked if t.invalid),
        "answered": interview.final is not None,
        "verdict": interview.final.value if interview.final else None,
        "truth": truth.truth.value,
        "still_open": still_open,
    }

    if interview.final is None:
        record["outcome"] = "stalled"
    elif interview.final is Verdict.CANNOT_DETERMINE:
        record["outcome"] = "abstained"
    elif still_open:
        record["outcome"] = "unsafe"
    elif interview.final is truth.truth:
        record["outcome"] = "correct"
    else:
        record["outcome"] = "wrong"
    return record


def score_all(interviews: list[Interview], oracle: Oracle,
              material_spread: float = 50.0) -> TrajectoryScore:
    s = TrajectoryScore(n=len(interviews))
    for iv in interviews:
        r = score_interview(iv, oracle, material_spread)
        s.questions_asked += r["questions"]
        s.questions_wasted += r["wasted"]
        s.questions_repeated += r["repeated"]
        s.questions_invalid += r["invalid"]
        s.detail.append(r)
        match r["outcome"]:
            case "stalled":
                s.stalled += 1
            case "abstained":
                s.abstained += 1
            case "unsafe":
                s.unsafe += 1
            case "correct":
                s.resolved_correct += 1
            case "wrong":
                s.resolved_wrong += 1
    return s
