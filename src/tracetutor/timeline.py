"""Variable timeline builder for TraceTutor."""

from __future__ import annotations

from dataclasses import dataclass

from tracetutor.state import TraceResult


@dataclass(frozen=True, slots=True)
class VariableTimelinePoint:
    """One visible value of a variable at a trace step."""

    step_index: int
    line_number: int | None
    value_repr: str
    type_name: str
    changed: bool


class VariableTimelineBuilder:
    """Build value history for one selected local variable."""

    @staticmethod
    def build(
        result: TraceResult,
        *,
        frame_depth: int,
        function_name: str,
        variable_name: str,
    ) -> tuple[VariableTimelinePoint, ...]:
        """Return timeline points for a variable selected in the UI."""
        points: list[VariableTimelinePoint] = []
        previous_value: str | None = None

        for step in result.steps:
            if frame_depth >= len(step.call_stack):
                continue

            frame = step.call_stack[frame_depth]
            if frame.function_name != function_name:
                continue

            variable = next(
                (
                    item
                    for item in frame.local_variables
                    if item.name == variable_name
                ),
                None,
            )
            if variable is None:
                continue

            changed = (
                previous_value is not None
                and variable.value_repr != previous_value
            )

            points.append(
                VariableTimelinePoint(
                    step_index=step.index,
                    line_number=step.line_number,
                    value_repr=variable.value_repr,
                    type_name=variable.type_name,
                    changed=changed,
                )
            )
            previous_value = variable.value_repr

        return tuple(points)