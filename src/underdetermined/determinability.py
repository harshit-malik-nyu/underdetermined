"""
Whether a benefits case can be decided at all, computed rather than labelled.

The application
---------------
Most benefit denials go unchallenged. Appeals succeed often — 67% of appealed
prior-authorisation denials are overturned in Medicare Advantage, 47% in
Medicaid managed care, 43% in the ACA Marketplace (KFF, 2025 insurer data) —
but appealing costs more effort than most claimants have. The bottleneck is
cognitive labour, which is the thing that just became cheap.

So the obvious application of an agent is: read the rules, assess the case,
file the claim. And the obvious objection is the one that matters. A wrong
filing can trigger fraud exposure, disqualify a claimant, or waste the one
appeal window they get. The error cost is asymmetric in the direction that
punishes the people least able to absorb it.

**That makes abstention the load-bearing capability, not accuracy.** An agent
that is right 95% of the time and cannot tell which 5% is wrong is unusable
here. An agent that is right 80% of the time and reliably says "I cannot
determine this from what you have given me" is deployable.

Nobody measures that, because it needs a ground truth for *undecidability*,
and undecidability is not something a human annotator can label reliably.

The construction
----------------
It does not have to be labelled. It can be computed.

Take a complete household. Compute the benefit with a rules engine. Now remove
a field — the claimant does not know it, or the form does not ask, or the
document is missing. Sweep that field across the values it plausibly could
have taken and recompute.

    the answer does not move   →  DETERMINABLE despite the gap.
                                  An agent should answer.

    the answer moves           →  UNDERDETERMINED.
                                  An agent that answers is guessing, and a
                                  guess here is a filed claim.

The threshold for "moves" is a policy choice and is stated, not hidden: a
spread large enough to change the decision a claimant would make.

This is ground truth by construction. No annotator is asked whether a case is
decidable; the rules engine is asked, and it answers the same way every time.

On the rules engine
-------------------
PolicyEngine (AGPL-3.0) implements the US tax-benefit system and is used here
as an oracle. It is not assumed correct in any absolute sense — it is an
implementation of published rules, with its own bugs, like any other. What it
provides is a *consistent* oracle: the same household always yields the same
answer, so determinability is a property of the case rather than of who was
asked.

Where its answer is wrong, the benchmark measures agreement with a wrong
oracle. That limitation is real and is recorded in docs/against.md rather than
argued away.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Verdict(str, Enum):
    """What an agent may say about a case."""

    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    CANNOT_DETERMINE = "cannot_determine"


class Determinability(str, Enum):
    """What the rules engine says about the case."""

    DETERMINABLE = "determinable"
    UNDERDETERMINED = "underdetermined"


# Fields a claimant plausibly might not know or might omit, with the range of
# values each could take. The ranges are deliberately conservative: wide enough
# to be realistic, narrow enough that a case is not called underdetermined
# because of an absurd hypothetical.
SWEEPABLE: dict[str, list[Any]] = {
    "dependents": [0, 1, 2, 3],
    "employment_income": [0, 9_000, 18_000, 27_000, 36_000],
    "age": [22, 35, 50, 64],
    "state_name": ["NY", "TX", "CA", "MS"],
}


@dataclass(frozen=True)
class Household:
    """A household described completely enough to compute a benefit."""

    employment_income: float = 18_000
    dependents: int = 0
    age: int = 35
    state_name: str = "NY"

    def replace(self, **kw) -> "Household":
        return Household(**{**self.__dict__, **kw})

    def to_situation(self, year: int = 2025) -> dict:
        people: dict[str, dict] = {
            "adult": {"age": {str(year): self.age},
                      "employment_income": {str(year): self.employment_income}}
        }
        members = ["adult"]
        for i in range(self.dependents):
            people[f"child{i}"] = {"age": {str(year): 8}}
            members.append(f"child{i}")
        return {
            "people": people,
            "families": {"f": {"members": members}},
            "spm_units": {"s": {"members": members}},
            "tax_units": {"t": {"members": members}},
            "households": {"h": {"members": members,
                                 "state_name": {str(year): self.state_name}}},
        }


@dataclass
class Case:
    """A household with some fields withheld, as an agent would receive it."""

    household: Household
    withheld: tuple[str, ...] = ()
    year: int = 2025

    def visible(self) -> dict:
        """What the agent is allowed to see."""
        return {k: v for k, v in self.household.__dict__.items()
                if k not in self.withheld}

    def describe(self) -> str:
        """A plain-language rendering, as a claimant might present it."""
        v = self.visible()
        parts = []
        if "employment_income" in v:
            parts.append(f"annual employment income of ${v['employment_income']:,.0f}")
        if "dependents" in v:
            n = v["dependents"]
            parts.append("no dependent children" if n == 0
                         else f"{n} dependent child{'ren' if n > 1 else ''}")
        if "age" in v:
            parts.append(f"aged {v['age']}")
        if "state_name" in v:
            parts.append(f"living in {v['state_name']}")
        body = "A single-adult household with " + ", ".join(parts) + "."
        if self.withheld:
            missing = ", ".join(w.replace("_", " ") for w in self.withheld)
            body += f" Not stated: {missing}."
        return body


# ---------------------------------------------------------------------------
# The oracle
# ---------------------------------------------------------------------------

class Oracle:
    """
    A rules engine, wrapped and cached.

    Caching matters: determinability requires sweeping every withheld field
    across its range, which is a combinatorial number of engine calls, and the
    engine is slow. Without the cache the benchmark takes hours.
    """

    def __init__(self, variable: str = "snap", year: int = 2025):
        self.variable = variable
        self.year = year
        self._cache: dict[tuple, float] = {}

    def benefit(self, hh: Household) -> float:
        key = (hh.employment_income, hh.dependents, hh.age, hh.state_name)
        if key in self._cache:
            return self._cache[key]
        from policyengine_us import Simulation
        sim = Simulation(situation=hh.to_situation(self.year))
        value = float(sim.calculate(self.variable, self.year)[0])
        self._cache[key] = value
        return value

    def eligible(self, hh: Household) -> bool:
        return self.benefit(hh) > 0


@dataclass
class DeterminabilityResult:
    case: Case
    label: Determinability
    truth: Verdict
    """What the answer is, when the case IS determinable. CANNOT_DETERMINE
    when it is not."""

    spread: float
    """How far the benefit moves across the withheld field's range."""

    outcomes: list[float] = field(default_factory=list)
    flips_eligibility: bool = False

    def as_dict(self) -> dict:
        return {
            "description": self.case.describe(),
            "withheld": list(self.case.withheld),
            "label": self.label.value,
            "truth": self.truth.value,
            "spread": self.spread,
            "flips_eligibility": self.flips_eligibility,
            "n_outcomes": len(self.outcomes),
        }


def assess(case: Case, oracle: Oracle, *,
           material_spread: float = 50.0) -> DeterminabilityResult:
    """
    Is this case decidable from what the agent can see?

    `material_spread` is the monthly benefit movement that counts as changing
    the answer. It is a policy choice and is exposed rather than buried: at
    zero, floating-point noise makes everything underdetermined; set too high,
    real differences are called immaterial.

    Eligibility flipping is treated as material regardless of spread, because
    eligible-versus-not is the decision a claimant acts on, and a case that
    flips it cannot be called determinable however small the dollar movement.
    """
    import itertools

    if not case.withheld:
        b = oracle.benefit(case.household)
        return DeterminabilityResult(
            case=case, label=Determinability.DETERMINABLE,
            truth=Verdict.ELIGIBLE if b > 0 else Verdict.NOT_ELIGIBLE,
            spread=0.0, outcomes=[b], flips_eligibility=False)

    ranges = [SWEEPABLE[w] for w in case.withheld]
    outcomes, eligibilities = [], []
    for combo in itertools.product(*ranges):
        hh = case.household.replace(**dict(zip(case.withheld, combo)))
        b = oracle.benefit(hh)
        outcomes.append(b)
        eligibilities.append(b > 0)

    spread = max(outcomes) - min(outcomes)
    flips = len(set(eligibilities)) > 1
    underdetermined = flips or spread > material_spread

    if underdetermined:
        label, truth = Determinability.UNDERDETERMINED, Verdict.CANNOT_DETERMINE
    else:
        label = Determinability.DETERMINABLE
        truth = Verdict.ELIGIBLE if eligibilities[0] else Verdict.NOT_ELIGIBLE

    return DeterminabilityResult(case=case, label=label, truth=truth,
                                 spread=spread, outcomes=outcomes,
                                 flips_eligibility=flips)
