"""Controlled execution of small Python pieces for educational tracing."""

from __future__ import annotations

import builtins
import io
import math
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from types import CodeType
from typing import Any

from tracetutor.exceptions import EmptyCodeError, StepLimitExceeded, UnsafeImportError
from tracetutor.state import EventKind, ExceptionSnapshot, TraceResult, TraceStep
from tracetutor.tracer import ExecutionTracer

TRACE_FILENAME = "<tracetutor-user-code>"


class CodeRunner:
    """Compile, execute and trace a small Python code piece."""

    def __init__(self, *, max_steps: int = 500) -> None:
        """Create a runner with a configurable trace step limit."""
        self._max_steps = max_steps

    @property
    def max_steps(self) -> int:
        """Return the maximum number of trace steps allowed for one run."""
        return self._max_steps

    def run(self, source_code: str) -> TraceResult:
        """Execute code and return a trace result.

        Args:
            source_code: Python code entered by the user.

        Returns:
            A ``TraceResult`` with steps, stdout and optional exception data.
        """
        source_lines = tuple(source_code.splitlines())
        if not source_code.strip():
            exception = ExceptionSnapshot("EmptyCodeError", "Code piece is empty", None)
            return TraceResult(
                source_lines=source_lines,
                steps=(
                    self._error_step(
                        source_lines=source_lines,
                        exception=exception,
                    ),
                ),
                stdout="",
                stderr="",
                exception=exception,
            )

        try:
            code = self._compile(source_code)
        except SyntaxError as exc:
            exception = ExceptionSnapshot(
                type_name=type(exc).__name__,
                message=exc.msg,
                line_number=exc.lineno,
            )
            return TraceResult(
                source_lines=source_lines,
                steps=(
                    self._error_step(
                        source_lines=source_lines,
                        exception=exception,
                    ),
                ),
                stdout="",
                stderr="",
                exception=exception,
            )

        tracer = ExecutionTracer(
            source_code,
            TRACE_FILENAME,
            max_steps=self._max_steps,
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        exception: ExceptionSnapshot | None = None
        old_trace = sys.gettrace()

        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                sys.settrace(tracer.trace)
                tracer.set_stdout(stdout.getvalue())
                namespace = self._build_globals()
                exec(code, namespace, namespace)
        except BaseException as exc:  # noqa: BLE001 - educational runner must report user errors
            exception = self._exception_from_runtime(exc)
        finally:
            sys.settrace(old_trace)

        return TraceResult(
            source_lines=source_lines,
            steps=self._attach_final_stdout(tracer.steps, stdout.getvalue()),
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
            exception=exception,
        )

    def _compile(self, source_code: str) -> CodeType:
        """Compile user code with a synthetic filename."""
        return compile(source_code, TRACE_FILENAME, "exec")

    def _build_globals(self) -> dict[str, Any]:
        """Create a limited global namespace for educational examples.

        This is not a security sandbox. It only removes the most obvious risky
        builtins from beginner-level examples.
        """
        allowed_builtin_names = {
            "ArithmeticError",
            "AssertionError",
            "BaseException",
            "Exception",
            "IndexError",
            "KeyError",
            "NameError",
            "RuntimeError",
            "StopIteration",
            "TypeError",
            "ValueError",
            "ZeroDivisionError",
            "__build_class__",
            "abs",
            "all",
            "any",
            "bool",
            "dict",
            "enumerate",
            "float",
            "int",
            "isinstance",
            "len",
            "list",
            "max",
            "min",
            "object",
            "print",
            "range",
            "repr",
            "reversed",
            "round",
            "set",
            "sorted",
            "str",
            "sum",
            "tuple",
            "type",
            "zip",
        }
        safe_builtins = {
            name: getattr(builtins, name)
            for name in allowed_builtin_names
            if hasattr(builtins, name)
        }
        safe_builtins["__import__"] = self._limited_import
        return {
            "__builtins__": safe_builtins,
            "__name__": "__tracetutor__",
        }

    @staticmethod
    def _limited_import(
        name: str,
        globals_: object | None = None,
        locals_: object | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        """Allow imports only from a tiny allowlist."""
        del globals_, locals_, fromlist, level
        if name == "math":
            return math
        raise UnsafeImportError(f"Import of module '{name}' is not allowed")

    @staticmethod
    def _attach_final_stdout(
        steps: tuple[TraceStep, ...],
        stdout: str,
    ) -> tuple[TraceStep, ...]:
        """Ensure the last rendered step shows final stdout."""
        if not steps:
            return steps
        *prefix, last = steps
        return (
            *prefix,
            TraceStep(
                index=last.index,
                event=last.event,
                line_number=last.line_number,
                function_name=last.function_name,
                source_line=last.source_line,
                call_stack=last.call_stack,
                stdout=stdout,
                return_value_repr=last.return_value_repr,
                exception=last.exception,
            ),
        )

    @staticmethod
    def _error_step(
        *,
        source_lines: tuple[str, ...],
        exception: ExceptionSnapshot,
    ) -> TraceStep:
        """Build a synthetic error step for errors before tracing starts."""
        line_number = exception.line_number
        source_line = ""
        if line_number is not None and 1 <= line_number <= len(source_lines):
            source_line = source_lines[line_number - 1].strip()
        return TraceStep(
            index=0,
            event=EventKind.EXCEPTION,
            line_number=line_number,
            function_name="<module>",
            source_line=source_line,
            call_stack=(),
            exception=exception,
        )

    @staticmethod
    def _exception_from_runtime(exc: BaseException) -> ExceptionSnapshot:
        """Convert a runtime exception into a serializable snapshot."""
        line_number = None
        for frame in traceback.extract_tb(exc.__traceback__):
            if frame.filename == TRACE_FILENAME:
                line_number = frame.lineno
        if isinstance(exc, StepLimitExceeded):
            line_number = None
        return ExceptionSnapshot(
            type_name=type(exc).__name__,
            message=str(exc),
            line_number=line_number,
        )
