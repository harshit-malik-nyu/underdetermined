# Can an assistant recognize that the evidence cannot settle a decision?

**Recommendation:** Score unsafe commitments, abstention and information-gathering cost separately; record every future model turn and transport failure.

This is an independent analytical case study. No client engagement, deployment, stakeholder acceptance or realized financial outcome is asserted.

## Decision and alternatives

Consider answer immediately; ask everything; ask only decision-relevant questions. The decision owner is the operator responsible for the workflow. An analyst owns evidence quality; the workflow owner owns review capacity and the acceptable error cost. These are proposed responsibilities, not named stakeholders who approved the work.

## Evidence and correction

Repeated and invalid questions count as waste. Transport errors raise and are recorded. Historical aggregate agent evidence cannot be converted into missing transcripts.

Frozen oracle tables and deterministic policies can be replayed offline; they are not fresh LLM trajectories. `analysis/output/manifest.json` identifies inputs, their hashes and observation counts. `analysis/questions.sql` exposes the aggregation and denominators; `analysis/build.py` rebuilds it locally. The source snapshot is the source of truth for descriptive claims. Earlier notebooks, figures and evidence JSON describe their original run unless explicitly regenerated.

## Economics and sensitivity

The current [executive decision summary](../analysis/output/decision_lab/executive-summary.md) compares **Ask every available question**, **Decision-relevant questions plus abstention**, and **Immediate answer from incomplete evidence**. The model separates Answer handling, Assistant turns, Information collection and escalation, User-assisted information collection.

The [assumption register](../analysis/decision_spec.json) labels all quantities, unit costs, incident rates and risk ceilings as planning assumptions. A 27-scenario grid varies volume, activity costs and incident risk. Risk and reviewer-capacity gates can veto the cheapest alternative. Expected-loss scenarios, salaried capacity and actual cash outlay are reported separately. The older `business_case.json` is a simple illustrative baseline, superseded for option selection by this richer model.

**Decision reversal:** If reduced question burden increases unsafe commitments, retain the safer policy even when it is slower.

## Product measurement

Primary metric: **Safe resolved cases / all cases, with abstentions and unsafe commitments separate.**

Guardrails: Repeated and invalid questions, unresolved cases and transport failures.

Completion includes the final decision or abstention; infrastructure failures remain outside behavioral scoring and are counted separately. Instrument each workflow with `started`, then one `completed` or `failed` event. Sessions still open remain incomplete in the denominator. `analysis/product.py` rejects duplicated events, invalid transitions, negative or nonfinite elapsed time, mixed evidence sources and unexpected fields. Only opaque session/event IDs, event type, elapsed milliseconds and evidence source are permitted. Do not log names, prompts, documents or case data.

The checked-in `events.synthetic.jsonl` is a small contract fixture: one completed, one failed and one incomplete session. Its completion rate is a QA expectation, not usage evidence. Actual adoption remains unmeasured. For an offline package, replaying known cases and validating these contracts is the achievable substitute for waiting on real users.

## Experiment and acceptance

For a future product comparison, randomly assign at the independent case or user level before exposure, keep assignment stable, and analyze intention-to-treat. Use an independent calibration split where thresholds are learned. Cluster repeated observations by household, paper, contract or user as appropriate. Fix the primary outcome and stopping point before inspection. Retain failures and attrition; do not remove hard cases after assignment.

Illustrative planning: a 50% baseline completion rate and a 5 percentage-point minimum effect require approximately 1,570 independent units per arm at two-sided 5% significance and 80% power using the conservative normal approximation. This is a design example, not an executed experiment or promised detectable effect under clustering. Multiply by the justified design effect for clustered units. A successful QA fixture does not substitute for this causal experiment.

For the delivered offline version, acceptance means all available offline regressions pass, evidence queries reconcile to input counts, deterministic rebuilds reproduce the same output hashes, and unsupported claims remain explicitly scoped. A statistical certificate additionally requires its documented iid, fixed-policy and calibration assumptions. If these fail, report inconclusive or infeasible rather than silently relaxing the threshold.

## Interview walkthrough

Explain the business decision first, then trace one result through the SQL to its source. Demonstrate the failure case that motivated the correction. Change an economic input and describe the decision boundary. Close by separating measured retrospective evidence, simulated validation and what remains unknown. This demonstrates data, business and product analysis without implying experience or outcomes the repository cannot establish.

## Product analysis and experiment decision

The decision laboratory supplies 2,560 explicitly synthetic assigned units across eight weekly cohorts and two project-specific segments. Its stage funnel uses all assigned units, including non-starters. D28 retention excludes immature cohorts; it never treats unobserved returns as failures. Segment results are exploratory.

**Stages:** case_opened → information_review_completed → safe_resolution_or_abstention_saved. **Guardrail incident:** unsupported commitment. **Unit:** evaluator account; repeated states and cases stay grouped within account. **Repeat-use interpretation:** evaluator returns for another eligible case batch.

The synthetic A/B decision uses intention-to-treat activation, an incident-rate guardrail, Wilson/Newcombe uncertainty, allocation diagnostics and a fixed-horizon sample-size plan. A primary metric win is insufficient when the guardrail fails. There is no real-world causal or adoption claim. Confirmatory rollout would require a prespecified population, meaningful minimum effect, acceptable incident margin and an appropriate cluster design; these are defined as requirements, not fabricated approvals.

**Prioritized next decisions:**

1. Retain turn-level transcripts and transport errors for every future run.
2. Compare ask-all, ask-relevant and answer-now on the same held-out cases.
3. Stop when further questions cannot settle the decision; do not reward forced answers.

The workflow-activation experiment is an adoption-mechanics study; it does not replace the domain quality metric above. The synthetic fixture deliberately includes a harmful treatment segment. Its hold result is a validation success, not evidence that a real product failed.
