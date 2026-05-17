"""Tests for variable timeline building."""

from textwrap import dedent

from tracetutor.runner import CodeRunner
from tracetutor.timeline import VariableTimelineBuilder


def test_variable_timeline_marks_changed_values() -> None:
    """Timeline should mark points where a variable value changes."""
    code = dedent(
        """
        x = 1
        x = 2
        x = 2
        x = 3
        """
    )

    result = CodeRunner().run(code)

    points = VariableTimelineBuilder.build(
        result,
        frame_depth=0,
        function_name="<module>",
        variable_name="x",
    )

    values = [point.value_repr for point in points]
    changed_flags = [point.changed for point in points]

    assert values == ["1", "2", "2", "3"]
    assert changed_flags == [False, True, False, True]
