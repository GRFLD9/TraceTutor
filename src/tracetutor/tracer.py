"""Trace collection based on Python's ``sys.settrace`` callback API."""

from __future__ import annotations

from collections.abc import Callable
from types import FrameType
from typing import Any

from tracetutor.exceptions import StepLimitExceeded
from tracetutor.state import (
    EventKind,
    ExceptionSnapshot,
    FrameSnapshot,
    TraceStep,
    VariableSnapshot,
)

TraceFunction = Callable[[FrameType, str, Any], "TraceFunction | None"]


class ExecutionTracer:
    """Collect trace steps for one compiled Python piece.

    The tracer records only frames whose filename is ``target_filename``.
    This keeps TraceTutor focused on the user's code and ignores Textual,
    pytest and internal project frames.
    """

    def __init__(
        self,
        source_code: str,
        target_filename: str,
        *,
        max_steps: int = 500,
        repr_limit: int = 120,
    ) -> None:
        """Create a tracer for one code piece.

        Args:
            source_code: User's Python code.
            target_filename: Synthetic filename used during ``compile``.
            max_steps: Maximum number of steps before execution is stopped.
            repr_limit: Maximum printable length for one variable representation.
        """
        self._source_lines = tuple(source_code.splitlines())
        self._target_filename = target_filename
        self._max_steps = max_steps
        self._repr_limit = repr_limit
        self._steps: list[TraceStep] = []
        self._last_stdout = ""
        self._operations = 0
        self._max_operations = max_steps * 50

    @property
    def steps(self) -> tuple[TraceStep, ...]:
        """Return all captured steps."""
        return tuple(self._steps)

    def set_stdout(self, stdout: str) -> None:
        """Store stdout text visible at the current trace step."""
        self._last_stdout = stdout

    def trace(self, frame: FrameType, event: str, arg: Any) -> TraceFunction | None:
        """Trace callback passed to ``sys.settrace``.

        Python calls this function on events such as ``call``, ``line``,
        ``return`` and ``exception``. Unsupported events are ignored.
        """
        if frame.f_code.co_filename != self._target_filename:
            return None

        frame.f_trace_opcodes = True
        self._tick()

        if event == "opcode":
            return self.trace

        if event == EventKind.CALL:
            self._record_step(frame, EventKind.CALL)
            return self.trace

        if event == EventKind.LINE:
            self._record_step(frame, EventKind.LINE)
            return self.trace

        if event == EventKind.RETURN:
            self._record_step(
                frame,
                EventKind.RETURN,
                return_value_repr=self._safe_repr(arg),
            )
            return self.trace

        if event == EventKind.EXCEPTION:
            exception = self._build_exception_snapshot(arg, frame.f_lineno)
            self._record_step(frame, EventKind.EXCEPTION, exception=exception)
            return self.trace

        return self.trace

    def _tick(self) -> None:
        """Count low-level traced operations to stop tight infinite loops."""
        self._operations += 1
        if self._operations > self._max_operations:
            raise StepLimitExceeded(self._max_steps)

    def _record_step(
        self,
        frame: FrameType,
        event: EventKind,
        *,
        return_value_repr: str | None = None,
        exception: ExceptionSnapshot | None = None,
    ) -> None:
        """Add one immutable step to the trace."""
        if len(self._steps) >= self._max_steps:
            raise StepLimitExceeded(self._max_steps)

        line_number = frame.f_lineno
        self._steps.append(
            TraceStep(
                index=len(self._steps),
                event=event,
                line_number=line_number,
                function_name=frame.f_code.co_name,
                source_line=self._source_line(line_number),
                call_stack=self._capture_stack(frame),
                stdout=self._last_stdout,
                return_value_repr=return_value_repr,
                exception=exception,
            )
        )

    def _capture_stack(self, frame: FrameType) -> tuple[FrameSnapshot, ...]:
        """Capture user-code frames from outermost to innermost."""
        frames: list[FrameSnapshot] = []
        current: FrameType | None = frame
        while current is not None:
            if current.f_code.co_filename == self._target_filename:
                frames.append(self._capture_frame(current))
            current = current.f_back
        return tuple(reversed(frames))

    def _capture_frame(self, frame: FrameType) -> FrameSnapshot:
        """Capture one frame without keeping references to live objects."""
        variables = [
            VariableSnapshot(
                name=name,
                value_repr=self._safe_repr(value),
                type_name=type(value).__name__,
            )
            for name, value in sorted(frame.f_locals.items())
            if self._should_show_variable(name)
        ]
        return FrameSnapshot(
            function_name=frame.f_code.co_name,
            line_number=frame.f_lineno,
            local_variables=tuple(variables),
        )

    @staticmethod
    def _should_show_variable(name: str) -> bool:
        """Hide implementation details from the variable table."""
        return not (name.startswith("__") and name.endswith("__"))

    def _source_line(self, line_number: int | None) -> str:
        """Return a source line by its 1-based number."""
        if line_number is None:
            return ""
        index = line_number - 1
        if 0 <= index < len(self._source_lines):
            return self._source_lines[index].strip()
        return ""

    def _safe_repr(self, value: Any) -> str:
        """Return a bounded ``repr`` that should not break the UI."""
        try:
            result = repr(value)
        except Exception as exc:  # pragma: no cover - rare defensive branch
            result = f"<repr failed: {type(exc).__name__}>"

        if len(result) > self._repr_limit:
            return result[: self._repr_limit - 3] + "..."
        return result

    def _build_exception_snapshot(
        self,
        arg: tuple[type[BaseException], BaseException, object],
        line_number: int,
    ) -> ExceptionSnapshot:
        """Convert ``sys.settrace`` exception argument to a dataclass."""
        exc_type, exc_value, _traceback = arg
        return ExceptionSnapshot(
            type_name=exc_type.__name__,
            message=str(exc_value),
            line_number=line_number,
        )
