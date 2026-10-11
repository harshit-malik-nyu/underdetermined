"""Toy-oracle regressions test mechanics, not benefit-law correctness."""
import pytest
from underdetermined.determinability import Household,Verdict,Case,assess
from underdetermined.interview import make_interview,Action,step
from underdetermined.policies import POLICIES,run_policy
from underdetermined.trajectory import score_all
from underdetermined import agent,interview_agent

class ToyOracle:
 def benefit(self,hh):return 100.0 if hh.employment_income<20000+5000*hh.dependents else 0.0
 def eligible(self,hh):return self.benefit(hh)>0


def test_reference_policies_with_independent_toy_oracle():
 oracle=ToyOracle();runs=[]
 for policy in POLICIES.values():
  for income in [10000,25000,100000]:
   iv=make_interview(Household(employment_income=income),budget=5)
   runs.append(run_policy(iv,policy,oracle))
 scored=score_all(runs,oracle)
 assert scored.n==12
 assert scored.unsafe>0 and scored.abstained>0 and scored.resolved_correct>0
 assert scored.questions_asked>0
 assert scored.as_dict()['safe_resolution_rate']==scored.resolved_correct/12
 assert 'UNSAFE' in scored.summary()


def test_repeated_and_invalid_questions_cost_budget_and_waste():
 o=ToyOracle();iv=make_interview(Household(),budget=2)
 step(iv,Action.ask('employment_income'),o);step(iv,Action.ask('invalid'),o)
 s=score_all([iv],o)
 assert s.stalled==1 and s.questions_wasted==2 and s.waste_rate==1
 assert s.questions_repeated==1 and s.questions_invalid==1
 with pytest.raises(RuntimeError):step(iv,Action.ask('age'),o)
 assert make_interview(Household(),volunteered=set()).known==set()


def test_model_transport_failure_is_not_abstention(monkeypatch):
 def fail(*a,**k):raise TimeoutError('fixture')
 monkeypatch.setattr(interview_agent,'_call',fail)
 record=[];iv=make_interview(Household())
 with pytest.raises(RuntimeError):interview_agent.agent_policy(recorder=record)(iv,ToyOracle(),50)
 assert record[0]['status']=='transport_error'
 assert iv.final is None
 monkeypatch.setattr(agent,'ask',fail)
 with pytest.raises(RuntimeError):agent.run_agent([assess(Case(Household()),ToyOracle())],recorder=record)
 assert record[-1]['status']=='transport_error'


def test_model_response_records_prompt_and_model(monkeypatch):
 monkeypatch.setattr(interview_agent,'_call',lambda *a:'ASK age')
 record=[];iv=make_interview(Household())
 action=interview_agent.agent_policy(recorder=record)(iv,ToyOracle(),50)
 assert action.field_name=='age'
 assert record[0]['response']=='ASK age' and record[0]['model']
 monkeypatch.setattr(agent,'ask',lambda *a:'ELIGIBLE')
 result=agent.run_agent([assess(Case(Household()),ToyOracle())],recorder=record)
 assert result==[Verdict.ELIGIBLE] and record[-1]['status']=='ok'

def test_unreliable_source_policies_respect_budget_and_terminate():
 from underdetermined.casefile import CaseFile
 from underdetermined.casefile_policies import POLICIES as FILE_POLICIES
 for policy in FILE_POLICIES.values():
  for seed in range(8):
   case=CaseFile(truth=Household(employment_income=25000,dependents=2),seed=seed)
   policy(case)
   assert case.finished
   assert case.budget_left()>=0
