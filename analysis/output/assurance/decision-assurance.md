# Decision assurance: underdetermined

Evaluate safe resolution, abstention and question burden separately. Favor decision-relevant questions only when a frozen policy clears the safety gate.

**Evidence:** Oracle cases expose withheld information, outcome spread and eligibility flips. Repeated/invalid questions count as waste; transport failures are separate from model abstention.

**Uncertainty:** The historical aggregate run lacks transcripts. Deterministic policy replay does not reproduce fresh model behavior.

## Robustness of the assumed business case

| Alternative | Feasible grid cases / 27 | Worst regret when feasible | Maximum volume at fixed review capacity |
|---|---:|---:|---:|
| Ask every available question | 3 | $31,025.00 | 12000 |
| Decision-relevant questions plus abstention | 6 | $0.00 | 21600 |
| Immediate answer from incomplete evidence | 0 | No feasible case | 108000 |

**Robust minimax choice:** None. No option is feasible across the entire stress grid.

Finite assumed grid, not a probability distribution or protection outside the grid. Conditional regret never overrides feasibility. Null robust option means no unconditional recommendation. Cost regret is relative to the cheapest feasible option in that same scenario. Failure counts can overlap.

## Missing-outcome sensitivity

| Outcomes masked per arm | Primary effect bounds | Incident effect bounds | Every completion clears margins? |
|---|---:|---:|---|
| 0% | [2.9%, 2.9%] | [0.9%, 0.9%] | False |
| 5% | [-1.8%, 8.2%] | [-4.1%, 5.9%] | False |
| 10% | [-6.7%, 13.3%] | [-8.9%, 11.1%] | False |
| 20% | [-16.9%, 23.1%] | [-19.1%, 20.9%] | False |

These are identification bounds on deliberately masked synthetic outcomes, not confidence intervals or measured missingness. Failures and non-starters remain in the assigned denominator. Passing this sensitivity check would still require statistical and domain-quality gates.

## Domain measurement contract

**Decision:** Choose when clarification is worth its burden and when an answer remains unsupported.

**Primary outcome:** Correct resolved decisions per eligible case, jointly with necessary questions, wasted questions and unresolved outcomes.

**Denominator:** All assigned cases; report transport failures, abstentions and invalid/repeated questions as separate categories.

**Independent unit:** Household or scenario family; multiple oracle states and trajectories may share the same underlying case.

**Quality guardrail:** Unsupported definitive answers, question burden and complete transcript/provenance coverage.

**Minimum required data:** Case/family ID, oracle provenance, available and withheld facts, complete question/answer transcript, policy version, result and transport status.

**Missingness and failure handling:** Never classify transport failure as deliberate abstention. Missing historical transcripts limit conclusions and cannot be reconstructed from aggregates.

**Release rule:** Use deterministic replay to validate policy logic, with a separate evidence label from fresh model behavior; unresolved facts prevent definitive decisions when they can flip the answer.

**Reversal trigger:** Question burden rises without reducing outcome ambiguity, or a withheld fact changes the claimed definitive answer.

## Interview defense

**Why ask fewer questions?**

Only when the remaining uncertainty cannot change the decision. Fewer questions alone is not success if correctness falls.

**Can replay validate historical model behavior?**

No. It validates the replayed policy under known cases. It cannot establish trajectories that were never recorded.

## Implementation handoff

1. Freeze the eligible population, denominator, outcome horizon and proposed decision owner before comparison.
2. Reconcile assignment and outcome records at the independence unit; classify missingness without deleting cases.
3. Estimate the domain outcome and its uncertainty separately from activation. Apply risk and capacity vetoes before comparing costs.
4. Record approve, hold, or reverse with the evidence version and violated gate. An unmeasured required domain gate means HOLD.

The supplied cluster-budget grid is a planning sensitivity check with assumed ICC. It is not an estimate from real clusters and does not guarantee joint power. No stakeholder approval or real experiment is asserted.
