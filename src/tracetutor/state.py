"""Immutable dataclasses that describe a captured execution trace."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EventKind(StrEnum):
    """Supported events produced by ``sys.settrace``."""

    CALL = "call"
    LINE = "line"
    RETURN = "return"
    EXCEPTION = "exception"


@dataclass(frozen=True, slots=True)
class VariableSnapshot:
    """A printable representation of one local variable."""

    name: str
    value_repr: str
    type_name: str


@dataclass(frozen=True, slots=True)
class FrameSnapshot:
    """A snapshot of one Python frame at a trace step."""

    function_name: str
    line_number: int
    local_variables: tuple[VariableSnapshot, ...]


@dataclass(frozen=True, slots=True)
class ExceptionSnapshot:
    """Information about an exception visible in the trace."""

    type_name: str
    message: str
    line_number: int | None = None

    @classmethod
    def from_empty_code(cls) -> "ExceptionSnapshot":
        """Create a snapshot for an empty user code piece."""
        return cls(
            type_name="EmptyCodeError",
            message="Code piece is empty",
            line_number=None,
        )

    @classmethod
    def from_syntax_error(cls, exc: SyntaxError) -> "ExceptionSnapshot":
        """Create a snapshot from a syntax error."""
        return cls(
            type_name=type(exc).__name__,
            message=exc.msg,
            line_number=exc.lineno,
        )

    @classmethod
    def from_exception(
            cls,
            exc: BaseException,
            *,
            line_number: int | None = None,
    ) -> "ExceptionSnapshot":
        """Create a snapshot from a runtime exception."""
        return cls(
            type_name=type(exc).__name__,
            message=str(exc),
            line_number=line_number,
        )


@dataclass(frozen=True, slots=True)
class TraceStep:
    """One captured step of Python execution."""

    index: int
    event: EventKind
    line_number: int | None
    function_name: str
    source_line: str
    call_stack: tuple[FrameSnapshot, ...]
    stdout: str = ""
    return_value_repr: str | None = None
    exception: ExceptionSnapshot | None = None


@dataclass(frozen=True, slots=True)
class TraceResult:
    """Full result of running and tracing a Python piece."""

    source_lines: tuple[str, ...]
    steps: tuple[TraceStep, ...]
    stdout: str
    stderr: str
    exception: ExceptionSnapshot | None = None

    @property
    def is_success(self) -> bool:
        """Return ``True`` when execution finished without an exception."""
        return self.exception is None
