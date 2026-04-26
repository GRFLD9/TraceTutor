"""Human-readable explanations for trace steps."""

from __future__ import annotations

from tracetutor.state import EventKind, TraceStep


class StepExplainer:
    """Build short educational comments for trace events."""

    def explain(self, step: TraceStep) -> str:
        """Return a short explanation for the given step."""
        location = self._format_location(step)

        if step.event == EventKind.CALL:
            return f"{location}: Python enters function `{step.function_name}`."

        if step.event == EventKind.LINE:
            return f"{location}: this source line is about to be executed."

        if step.event == EventKind.RETURN:
            return (
                f"{location}: function `{step.function_name}` returns "
                f"{step.return_value_repr}."
            )

        if step.event == EventKind.EXCEPTION and step.exception is not None:
            return (
                f"{location}: exception `{step.exception.type_name}` was raised: "
                f"{step.exception.message}"
            )

        return f"{location}: trace event `{step.event}`."

    @staticmethod
    def _format_location(step: TraceStep) -> str:
        """Format a compact step location."""
        if step.line_number is None:
            return f"Step {step.index}"
        return f"Step {step.index}, line {step.line_number}"
