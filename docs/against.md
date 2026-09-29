# The case against this benchmark

The strongest argument that it should not be trusted.

---

## 1. The oracle is not truth, it is an implementation

PolicyEngine implements published US benefit rules. It has bugs, like every
implementation. Where its answer is wrong, this benchmark measures **agreement
with a wrong oracle**, and an agent that correctly disagreed would be scored
as failing.

What the construction does give is *consistency*: the same household always
yields the same answer, so determinability is a property of the case rather
than of which annotator was asked. That is weaker than correctness and is the
right claim to make.

**This is the most serious objection**, and it is not fixable without
validating the engine against adjudicated cases, which nobody has published.

## 2. The sweep ranges are a judgement call

A case is underdetermined if the answer moves across the values a missing
field "plausibly could have taken". Those ranges are stipulated in
`SWEEPABLE`, and widening them makes more cases underdetermined.

Income is swept 0–36,000. If a claimant could plausibly earn 80,000, cases
currently labelled determinable would flip. The ranges are conservative and
visible, and someone who disagrees can change one dictionary and re-label —
but the labels move when they do.

## 3. Material spread is a threshold with no principled value

$50 a month. Below it, a difference is called immaterial. That number decides
which cases are underdetermined and it is chosen, not derived. Eligibility
flipping is treated as material regardless, which covers the worst case, but
the dollar threshold is arbitrary between "changes nothing" and "changes
everything".

## 4. The household model is far simpler than real cases

Four fields. Real SNAP determinations involve assets, deductions, shelter
costs, immigration status, work requirements, categorical eligibility and
state waivers. A benchmark this simple **overstates** how determinable real
cases are, so an agent scoring well here has not been tested on the hard part.

## 5. The descriptions are generated, not written by claimants

Real intake text is ambiguous, contradictory, and often omits things without
signalling that it has. Here the missing fields are named explicitly — "Not
stated: dependents" — which is a large hint. An agent facing real text has to
notice the gap *and* reason about it; this only tests the second.

## 6. Abstention is not free and the benchmark treats it as nearly so

The unsafe rate is the headline and coverage is reported beside it, but there
is no weight on them. In deployment, a claimant told "I cannot determine this"
may get no help at all, which is its own harm — and one this scoring cannot
see because the benchmark has no model of what happens after abstention.

## 7. No agent has been run on it

The reference policies bracket the problem, and the interesting question —
whether a reasoning agent beats the safe heuristic — is unanswered. Until it
is, this is a measuring instrument with nothing measured.

---

## What survives

- **Determinability is computed, not labelled.** Whatever else is wrong, the
  labels are reproducible and auditable.
- **The discrimination is real.** The gap between the safe heuristic and the
  ceiling is 29.6 points, and it exists because missing fields are sometimes
  irrelevant — which is a fact about the rules, not about the construction.
- **The metric resists the degenerate policy.** Abstaining on everything is
  detected and flagged rather than scoring perfectly.

## The objection I cannot answer

Argument 1. Without an engine validated against adjudicated determinations,
this measures agreement rather than correctness, and no amount of careful
construction on top of it changes that.
