"""
Tests for the determinability benchmark.

Several pin the interpretation rather than the code, because the way this
benchmark fails is by being read wrongly — an unsafe rate quoted without
coverage recommends abstaining on everything.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from underdetermined.benchmark import (
    abstain_if_anything_missing, always_abstain, always_answer,
    build_benchmark, oracle_policy, score,
)
from underdetermined.determinability import (
    SWEEPABLE, Case, Determinability, DeterminabilityResult, Household, Verdict,
)

ROOT = Path(__file__).resolve().parents[1]


def fake(label, truth, withheld=()):
    return DeterminabilityResult(
        case=Case(Household(), withheld), label=label, truth=truth,
        spread=0.0 if label is Determinability.DETERMINABLE else 5000.0)


class TestHousehold:

    def test_withheld_fields_are_hidden(self):
        c = Case(Household(employment_income=24000, dependents=2), ("dependents",))
        assert "dependents" not in c.visible()
        assert "employment_income" in c.visible()

    def test_description_names_what_is_missing(self):
        d = Case(Household(), ("dependents", "age")).describe()
        assert "Not stated" in d and "dependents" in d and "age" in d

    def test_description_of_a_complete_case_states_no_gap(self):
        assert "Not stated" not in Case(Household()).describe()

    def test_every_sweepable_field_exists_on_the_household(self):
        for f in SWEEPABLE:
            assert hasattr(Household(), f), f"{f} is swept but is not a field"


class TestScoring:

    def test_unsafe_means_answering_an_undecidable_case(self):
        r = [fake(Determinability.UNDERDETERMINED, Verdict.CANNOT_DETERMINE)] * 4
        assert score(r, [Verdict.ELIGIBLE] * 4).unsafe_rate == 1.0

    def test_abstaining_on_undecidable_cases_is_safe(self):
        r = [fake(Determinability.UNDERDETERMINED, Verdict.CANNOT_DETERMINE)] * 4
        assert score(r, [Verdict.CANNOT_DETERMINE] * 4).unsafe_rate == 0.0

    def test_coverage_counts_determinable_cases_resolved(self):
        r = ([fake(Determinability.DETERMINABLE, Verdict.ELIGIBLE)] * 3
             + [fake(Determinability.DETERMINABLE, Verdict.NOT_ELIGIBLE)])
        s = score(r, [Verdict.ELIGIBLE, Verdict.ELIGIBLE,
                      Verdict.CANNOT_DETERMINE, Verdict.NOT_ELIGIBLE])
        assert s.coverage == pytest.approx(0.75)

    def test_the_degenerate_policy_is_flagged(self):
        """
        Abstaining on everything scores a perfect unsafe rate. A metric that
        cannot see this recommends a worthless agent.
        """
        r = [fake(Determinability.DETERMINABLE, Verdict.ELIGIBLE)] * 10
        s = score(r, always_abstain(r))
        assert s.unsafe_rate == 0.0
        assert s.abstains_on_everything
        assert "worth nothing" in s.summary()

    def test_summary_never_gives_safety_without_coverage(self):
        r = [fake(Determinability.UNDERDETERMINED, Verdict.CANNOT_DETERMINE)] * 5
        d = score(r, always_abstain(r)).as_dict()
        assert "unsafe_rate" in d and "coverage" in d

    def test_mismatched_lengths_are_refused(self):
        with pytest.raises(ValueError):
            score([fake(Determinability.DETERMINABLE, Verdict.ELIGIBLE)], [])


class TestReferencePolicies:

    @pytest.fixture
    def results(self):
        return ([fake(Determinability.UNDERDETERMINED, Verdict.CANNOT_DETERMINE,
                      ("dependents",))] * 5
                + [fake(Determinability.DETERMINABLE, Verdict.ELIGIBLE)] * 5)

    def test_always_answer_is_maximally_unsafe(self, results):
        assert score(results, always_answer(results)).unsafe_rate == 1.0

    def test_always_abstain_has_no_coverage(self, results):
        assert score(results, always_abstain(results)).coverage == 0.0

    def test_the_heuristic_is_safe(self, results):
        assert score(results, abstain_if_anything_missing(results)).unsafe_rate == 0.0

    def test_the_oracle_is_the_ceiling(self, results):
        s = score(results, oracle_policy(results))
        assert s.unsafe_rate == 0.0 and s.coverage == 1.0


class TestBenchmarkGeneration:

    def test_cases_span_the_eligibility_boundary(self):
        cases = build_benchmark(200, seed=3)
        incomes = {c.household.employment_income for c in cases}
        assert min(incomes) == 0 and max(incomes) >= 42_000 and len(incomes) >= 5

    def test_some_cases_are_complete(self):
        assert any(not c.withheld for c in build_benchmark(200, seed=3))

    def test_some_cases_withhold_two_fields(self):
        assert any(len(c.withheld) == 2 for c in build_benchmark(300, seed=3))

    def test_generation_is_reproducible(self):
        a = [c.describe() for c in build_benchmark(30, seed=7)]
        b = [c.describe() for c in build_benchmark(30, seed=7)]
        assert a == b


class TestAgentHarness:

    def test_verdicts_parse(self):
        from underdetermined.agent import parse_verdict
        assert parse_verdict("ELIGIBLE") is Verdict.ELIGIBLE
        assert parse_verdict("  not_eligible ") is Verdict.NOT_ELIGIBLE
        assert parse_verdict("CANNOT_DETERMINE") is Verdict.CANNOT_DETERMINE

    def test_an_unparseable_reply_counts_as_abstention(self):
        """
        Not dropped. Dropping would remove the agent's worst cases from the
        denominator.
        """
        from underdetermined.agent import parse_verdict
        assert parse_verdict("hello") is Verdict.CANNOT_DETERMINE
        assert parse_verdict("") is Verdict.CANNOT_DETERMINE

    def test_not_eligible_is_not_read_as_eligible(self):
        from underdetermined.agent import parse_verdict
        assert parse_verdict("NOT ELIGIBLE") is Verdict.NOT_ELIGIBLE

    def test_the_harness_refuses_to_simulate_a_model(self):
        import os

        from underdetermined.agent import AgentConfig, ask
        os.environ.pop("DEFINITELY_NOT_SET_XYZ", None)
        with pytest.raises(RuntimeError, match="does not simulate"):
            ask("anything", AgentConfig(api_key_env="DEFINITELY_NOT_SET_XYZ"))

    def test_the_prompt_is_not_engineered(self):
        from underdetermined.agent import SYSTEM
        low = SYSTEM.lower()
        assert "step by step" not in low and "for example" not in low
        assert len(SYSTEM) < 700


class TestCommittedEvidence:

    @pytest.fixture(scope="class")
    def baselines(self):
        p = ROOT / "evidence" / "baselines.json"
        if not p.exists():
            pytest.skip("no committed run")
        return {r["policy"]: r for r in json.loads(p.read_text())}

    def test_the_naive_agent_is_fully_unsafe(self, baselines):
        assert baselines["always answer"]["unsafe_rate"] == 1.0

    def test_the_heuristic_leaves_coverage_on_the_table(self, baselines):
        h = baselines["abstain if anything missing"]["coverage"]
        o = baselines["oracle (ceiling)"]["coverage"]
        assert h < o - 0.1, "benchmark no longer discriminates"

    def test_the_benchmark_is_not_all_one_class(self, baselines):
        b = baselines["oracle (ceiling)"]
        share = b["n_underdetermined"] / b["n"]
        assert 0.2 < share < 0.8, f"class balance is {share:.0%}"


class TestOracle:
    """
    Exercises the rules engine. Skipped where it is not installed, because the
    benchmark data is committed and evaluating an agent does not need it.
    """

    @pytest.fixture(scope="class")
    def oracle(self):
        pytest.importorskip("policyengine_us")
        from underdetermined.determinability import Oracle
        return Oracle()

    def test_a_complete_case_is_always_determinable(self, oracle):
        from underdetermined.determinability import assess
        r = assess(Case(Household(employment_income=18_000)), oracle)
        assert r.label is Determinability.DETERMINABLE
        assert r.spread == 0.0

    def test_a_missing_field_that_matters_makes_it_undetermined(self, oracle):
        from underdetermined.determinability import assess
        r = assess(Case(Household(employment_income=24_000, dependents=2),
                        ("dependents",)), oracle)
        assert r.label is Determinability.UNDERDETERMINED
        assert r.flips_eligibility

    def test_a_missing_field_that_does_not_matter_leaves_it_determinable(self, oracle):
        """
        THE POINT OF THE BENCHMARK. At an income far above every threshold,
        dependent count cannot change the answer — so an agent that abstains
        here is being needlessly unhelpful, not safe.
        """
        from underdetermined.determinability import assess
        r = assess(Case(Household(employment_income=60_000, dependents=0),
                        ("dependents",)), oracle)
        assert r.label is Determinability.DETERMINABLE

    def test_the_oracle_caches(self, oracle):
        hh = Household(employment_income=12_000)
        oracle.benefit(hh)
        n = len(oracle._cache)
        oracle.benefit(hh)
        assert len(oracle._cache) == n


class TestCLI:

    def test_evaluate_loads_committed_labels_without_the_oracle(self, tmp_path):
        """
        Evaluating an agent must not require the rules engine. Labels are
        committed; re-deriving them would make the benchmark unusable to
        anyone who cannot install an AGPL dependency.
        """
        import json

        from underdetermined.evaluate import load
        p = tmp_path / "b.json"
        p.write_text(json.dumps([{
            "description": "A household with income.", "withheld": ["dependents"],
            "label": "underdetermined", "truth": "cannot_determine",
            "spread": 4000.0, "flips_eligibility": True, "n_outcomes": 4,
        }]))
        results = load(p)
        assert len(results) == 1
        assert results[0].label is Determinability.UNDERDETERMINED
        assert results[0].case.describe() == "A household with income."

    def test_build_accepts_its_arguments(self):
        from underdetermined.build import main
        import inspect
        src = inspect.getsource(main)
        for flag in ("--n", "--seed", "--material-spread"):
            assert flag in src

    def test_material_spread_is_exposed_not_buried(self):
        """
        The threshold deciding which cases are underdetermined is a policy
        choice and must be settable from the command line.
        """
        from underdetermined.determinability import assess
        import inspect
        assert "material_spread" in inspect.signature(assess).parameters


class TestInterview:
    """The agentic version: the agent must decide what to ask."""

    def test_the_description_does_not_name_missing_fields(self):
        """
        THE FIX. The first benchmark appended 'Not stated: dependents', which
        hands over the hard half of the problem. A real intake gives you what
        someone thought to mention.
        """
        from underdetermined.interview import make_interview
        iv = make_interview(Household(employment_income=18000))
        d = iv.describe()
        assert "Not stated" not in d
        assert "dependents" not in d
        assert "18,000" in d

    def test_unknown_fields_are_visible_to_the_environment_only(self):
        from underdetermined.interview import make_interview
        iv = make_interview(Household())
        assert "dependents" in iv.unknown()
        assert "dependents" not in iv.describe()

    def test_asking_consumes_budget(self):
        from underdetermined.interview import Action, make_interview, step
        iv = make_interview(Household(), budget=2)
        step(iv, Action.ask("dependents"), _NullOracle())
        assert iv.budget_left() == 1

    def test_budget_exhaustion_finishes_without_an_answer(self):
        """
        Stalling is a failure with its own name, not a silently forgiven
        outcome: the claimant's time was spent and they got nothing.
        """
        from underdetermined.interview import Action, make_interview, step
        iv = make_interview(Household(), budget=1)
        step(iv, Action.ask("dependents"), _NullOracle())
        assert iv.finished and iv.final is None

    def test_repeated_questions_are_recorded(self):
        from underdetermined.interview import Action, make_interview, step
        iv = make_interview(Household(), budget=4)
        step(iv, Action.ask("dependents"), _NullOracle())
        t = step(iv, Action.ask("dependents"), _NullOracle())
        assert t.repeated and t.informative is False

    def test_answering_a_finished_interview_is_refused(self):
        from underdetermined.interview import Action, make_interview, step
        iv = make_interview(Household())
        step(iv, Action.answer(Verdict.ELIGIBLE), _NullOracle())
        with pytest.raises(RuntimeError):
            step(iv, Action.answer(Verdict.ELIGIBLE), _NullOracle())


class _NullOracle:
    """Stands in where a turn's bookkeeping is under test, not its value."""

    def benefit(self, hh):
        return 0.0

    def eligible(self, hh):
        return False


class TestTrajectoryScoring:

    def test_the_three_failures_are_reported_together(self):
        """
        Any one alone recommends a degenerate policy: never ask, always ask,
        or never answer.
        """
        from underdetermined.trajectory import TrajectoryScore
        d = TrajectoryScore(n=1).as_dict()
        for k in ("unsafe_rate", "waste_rate", "stall_rate", "resolution_rate"):
            assert k in d

    def test_asking_everything_is_flagged(self):
        from underdetermined.trajectory import TrajectoryScore
        s = TrajectoryScore(n=10, questions_asked=30, questions_wasted=20)
        assert s.asks_everything
        assert "claimant's time" in s.summary()

    def test_waste_rate_is_zero_when_nothing_is_asked(self):
        from underdetermined.trajectory import TrajectoryScore
        assert TrajectoryScore(n=5).waste_rate == 0.0


class TestInterviewAgent:

    def test_ask_is_parsed(self):
        from underdetermined.interview_agent import parse_action
        from underdetermined.interview import Move
        a = parse_action("ASK dependents")
        assert a.move is Move.ASK and a.field_name == "dependents"

    def test_answers_are_parsed(self):
        from underdetermined.interview_agent import parse_action
        from underdetermined.interview import Move
        assert parse_action("ANSWER NOT_ELIGIBLE").verdict is Verdict.NOT_ELIGIBLE
        assert parse_action("ANSWER ELIGIBLE").verdict is Verdict.ELIGIBLE
        assert parse_action("ANSWER CANNOT_DETERMINE").move is Move.ANSWER

    def test_malformed_replies_become_abstention_not_a_retry(self):
        from underdetermined.interview_agent import parse_action
        from underdetermined.interview import Move
        a = parse_action("I'm not sure what you want")
        assert a.move is Move.ANSWER and a.verdict is Verdict.CANNOT_DETERMINE

    def test_the_prompt_lists_fields_but_is_not_engineered(self):
        from underdetermined.interview_agent import SYSTEM
        low = SYSTEM.lower()
        assert "employment_income" in low
        assert "step by step" not in low and "for example" not in low


class TestInterviewPolicies:

    @pytest.fixture(scope="class")
    def oracle(self):
        pytest.importorskip("policyengine_us")
        from underdetermined.determinability import Oracle
        return Oracle()

    def test_informativeness_is_conditional_on_what_is_known(self, oracle):
        """
        THE AGENTIC STRUCTURE. A field worthless now can be decisive after
        another is learned, so no static list of questions is correct.
        """
        from underdetermined.interview import (
            Action, informative_now, make_interview, step)
        hh = Household(employment_income=24000, dependents=2, age=35,
                       state_name="NY")
        iv = make_interview(hh)
        before = informative_now(iv, "state_name", oracle)
        step(iv, Action.ask("dependents"), oracle)
        after = informative_now(iv, "state_name", oracle)
        assert before != after, "informativeness should move with knowledge"

    def test_nothing_is_worth_asking_when_the_case_is_already_decided(self, oracle):
        from underdetermined.interview import informative_now, make_interview
        iv = make_interview(Household(employment_income=60000, dependents=0))
        assert not any(informative_now(iv, f, oracle) for f in iv.unknown())
