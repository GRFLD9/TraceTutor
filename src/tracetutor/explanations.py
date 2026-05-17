"""Human-readable explanations for trace steps."""

from __future__ import annotations

from typing import Protocol

from tracetutor.state import EventKind, TraceStep


class ExplainerProtocol(Protocol):
    """Interface for objects that can explain trace steps."""

    def explain(self, step: TraceStep) -> str:
        """Return a short explanation for the given step."""
        ...


class StepExplainer:
    """Build short educational comments for trace events."""

    def explain(self, step: TraceStep) -> str:
        """Return a short explanation for the given step."""
        location = self._format_location(step)

        if step.event == EventKind.CALL:
            return f"{location}: Python enters function `{step.function_name}`."

        if step.event == EventKind.LINE:
            return self._explain_line(step, location)

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

    def _explain_line(self, step: TraceStep, location: str) -> str:
        """Explain a source line before it is executed."""
        source_line = step.source_line.strip()

        if not source_line:
            return f"{location}: Python is about to execute an empty line."

        if source_line.startswith("for "):
            return (
                f"{location}: Python starts or continues a loop. "
                "The loop variable and loop body may update local state."
            )

        if source_line.startswith("while "):
            return (
                f"{location}: Python checks a while-loop condition. "
                "If it is true, the loop body will run again."
            )

        if source_line.startswith("if "):
            return (
                f"{location}: Python checks a condition and chooses "
                "which branch should be executed."
            )

        if source_line.startswith("return"):
            return (
                f"{location}: Python is about to leave the current function "
                "and send a value back to the caller."
            )

        if "print(" in source_line:
            return (
                f"{location}: this line writes a value to stdout, "
                "so it will appear in the output panel."
            )

        if self._looks_like_assignment(source_line):
            return (
                f"{location}: this line assigns or updates a variable. "
                "The local state may change after this step."
            )

        return f"{location}: this source line is about to be executed."

    @staticmethod
    def _looks_like_assignment(source_line: str) -> bool:
        """Return whether a source line looks like an assignment."""
        if "==" in source_line or "!=" in source_line or "<=" in source_line or ">=" in source_line:
            return False
        return "=" in source_line

    @staticmethod
    def _format_location(step: TraceStep) -> str:
        """Format a compact step location."""
        if step.line_number is None:
            return f"Step {step.index}"
        return f"Step {step.index}, line {step.line_number}"
