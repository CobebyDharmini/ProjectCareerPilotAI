from services.analysis_advisor import build_skill_action_plan


def test_skill_action_plan_preserves_gap_priority_order() -> None:
    plan = build_skill_action_plan(("SQL", "Python"))
    assert [action.skill for action in plan] == ["SQL", "Python"]


def test_skill_action_plan_includes_learning_and_project_guidance() -> None:
    action = build_skill_action_plan(("SQL",))[0]
    assert action.learning_url == "https://sqlbolt.com/"
    assert "SQLite" in action.project_idea
    assert action.practice_activity


def test_unknown_dictionary_skill_receives_generic_guidance() -> None:
    action = build_skill_action_plan(("Example skill",))[0]
    assert "Example skill" in action.practice_activity
    assert "Example skill" in action.project_idea
    assert action.learning_url is None


def test_empty_gap_list_returns_no_actions() -> None:
    assert build_skill_action_plan(()) == ()