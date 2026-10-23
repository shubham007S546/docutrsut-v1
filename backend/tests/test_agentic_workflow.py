from backend.agents.contracts import Evidence, SAFE_TOOLS
from backend.graph.workflow import supervisor_plan


def test_privacy_query_routes_only_relevant_specialists():
    plan = supervisor_plan("Does this policy retain personal data?")
    agents = [task.agent for task in plan.subtasks]
    assert "privacy" in agents
    assert "security" not in agents


def test_security_query_routes_security():
    plan = supervisor_plan("Does this policy require MFA for access?")
    assert "security" in [task.agent for task in plan.subtasks]


def test_conflict_query_routes_conflict_and_verification():
    plan = supervisor_plan("Find conflicting rules between policy versions")
    agents = [task.agent for task in plan.subtasks]
    assert "conflict" in agents
    assert "verification" in agents
    assert plan.max_iterations == 3


def test_planner_has_allowlisted_tools_only():
    plan = supervisor_plan("What does the policy require?")
    assert set(plan.selected_tools).issubset(SAFE_TOOLS)

