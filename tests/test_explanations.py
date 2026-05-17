"""Tests for human-readable step explanations."""

from tracetutor.explanations import StepExplainer
from tracetutor.state import EventKind, TraceStep


def make_line_step(source_line: str) -> TraceStep:
    """Create a minimal line step for explanation tests."""
    return TraceStep(
        index=0,
        event=EventKind.LINE,
        line_number=1,
        function_name="<module>",
        source_line=source_line,
        call_stack=(),
    )


def test_explainer_detects_assignment() -> None:
    """Assignment lines should mention state updates."""
    explanation = StepExplainer().explain(make_line_step("x = 1"))

    assert "assigns or updates" in explanation
    assert "local state" in explanation


def test_explainer_detects_loop() -> None:
    """Loop lines should mention repeated execution."""
    explanation = StepExplainer().explain(make_line_step("for x in range(3):"))

    assert "loop" in explanation


def test_explainer_detects_condition() -> None:
    """Condition lines should mention branch choice."""
    explanation = StepExplainer().explain(make_line_step("if x > 0:"))

    assert "condition" in explanation
    assert "branch" in explanation


def test_explainer_detects_print() -> None:
    """Print lines should mention stdout."""
    explanation = StepExplainer().explain(make_line_step("print(x)"))

    assert "stdout" in explanation


def test_explainer_detects_return() -> None:
    """Return lines should mention leaving a function."""
    explanation = StepExplainer().explain(make_line_step("return x"))

    assert "leave the current function" in explanation
