"""Project-specific exceptions used by TraceTutor."""


class TraceTutorError(Exception):
    """Base class for all TraceTutor errors."""


class EmptyCodeError(TraceTutorError):
    """Raised when the user tries to execute an empty code."""


class StepLimitExceeded(TraceTutorError):
    """Raised when traced code produces too many execution steps."""

    def __init__(self, max_steps: int) -> None:
        """Store the configured step limit in the error message."""
        super().__init__(f"Execution stopped after {max_steps} trace steps")
        self.max_steps = max_steps


class UnsafeImportError(TraceTutorError):
    """Raised when traced code imports a module outside the allowlist."""
