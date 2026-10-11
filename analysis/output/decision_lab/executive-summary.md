# Buy useful information before asking more questions or forcing an answer

Evaluate safe resolution, abstention and question burden separately. Favor decision-relevant questions only when a frozen policy clears the safety gate.

**Observed evidence:** Oracle cases expose withheld information, outcome spread and eligibility flips. Repeated/invalid questions count as waste; transport failures are separate from model abstention.

**Decision owner:** Assistant evaluation lead (proposed role, not a client).

**Base planning case:** Decision-relevant questions plus abstention. This is conditional on the assumptions, not deployment approval.

| Alternative | Economic cost | Cash outlay | Reviewer hours | Passes risk and capacity |
|---|---:|---:|---:|---|
| Ask every available question | $140,400 | $5,400 | 2,700.0 | False |
| Decision-relevant questions plus abstention | $93,700 | $18,700 | 1,500.0 | True |
| Immediate answer from incomplete evidence | $18,540 | $3,540 | 300.0 | False |

Economic cost includes valued staff capacity and scenario incident losses. Cash outlay excludes salaried capacity and contingent losses. These are not realized savings.

**Sensitivity across 27 equally enumerated scenarios:** Decision-relevant questions plus abstention: 6, NO FEASIBLE OPTION: 21. Grid counts are not probabilities.

**Synthetic product experiment:** HOLD. Primary effect 2.9%; 95% interval [-0.9%, 6.7%]. Guardrail effect 0.9%; interval [0.2%, 1.7%]. These numbers test the decision logic, not product performance.

**Priority order:**

1. Retain turn-level transcripts and transport errors for every future run.
2. Compare ask-all, ask-relevant and answer-now on the same held-out cases.
3. Stop when further questions cannot settle the decision; do not reward forced answers.

**What would reverse the recommendation:** If reduced question burden increases unsafe commitments, retain the safer policy even when it is slower.

**Remaining uncertainty:** The historical aggregate run lacks transcripts. Deterministic policy replay does not reproduce fresh model behavior.
