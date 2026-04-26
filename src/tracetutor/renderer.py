"""Textual-based interface for TraceTutor."""

from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Label, RichLog, TextArea

from tracetutor.explanations import StepExplainer
from tracetutor.runner import CodeRunner
from tracetutor.state import FrameSnapshot, TraceResult, TraceStep

DEFAULT_CODE = """def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

answer = factorial(4)
print(answer)
"""


class TraceTutorApp(App[None]):
    """Interactive TUI application for stepping through Python traces."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #main {
        height: 1fr;
        layout: horizontal;
    }

    #left-pane {
        width: 45%;
        min-width: 40;
        padding: 1;
    }

    #right-pane {
        width: 55%;
        padding: 1;
    }

    #code-input {
        height: 1fr;
        border: round $accent;
    }

    #buttons {
        height: auto;
        margin-top: 1;
    }

    #status {
        height: 3;
        content-align: left middle;
    }

    .panel {
        height: 1fr;
        border: round $primary;
        margin-bottom: 1;
    }

    #source-view {
        height: 2fr;
    }

    #variables-table {
        height: 1fr;
    }

    #stack-table {
        height: 1fr;
    }

    #explanation-log {
        height: 1fr;
    }
    """

    BINDINGS = [
        ("r", "run_trace", "Run"),
        ("n", "next_step", "Next"),
        ("p", "previous_step", "Prev"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, initial_code: str = DEFAULT_CODE) -> None:
        """Create the UI with optional initial code."""
        super().__init__()
        self._initial_code = initial_code
        self._runner = CodeRunner()
        self._explainer = StepExplainer()
        self._result: TraceResult | None = None
        self._current_step_index = 0

    def compose(self) -> ComposeResult:
        """Build the Textual widget tree."""
        yield Header(show_clock=True)
        with Container(id="main"):
            with Vertical(id="left-pane"):
                yield Label("Python code")
                yield TextArea.code_editor(
                    self._initial_code,
                    language="python",
                    id="code-input",
                )
                with Horizontal(id="buttons"):
                    yield Button("Run", id="run", variant="success")
                    yield Button("Prev", id="prev")
                    yield Button("Next", id="next", variant="primary")
                yield Label("Press r=run, n=next, p=prev, q=quit", id="status")
            with Vertical(id="right-pane"):
                yield Label("Current source line")
                yield RichLog(id="source-view", classes="panel", wrap=True, highlight=True)
                yield Label("Local variables")
                yield DataTable(id="variables-table", classes="panel")
                yield Label("Call stack")
                yield DataTable(id="stack-table", classes="panel")
                yield Label("Explanation and stdout")
                yield RichLog(id="explanation-log", classes="panel", wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        """Prepare tables when the app starts."""
        variables = self.query_one("#variables-table", DataTable)
        variables.add_columns("frame", "name", "type", "value")
        variables.zebra_stripes = True

        stack = self.query_one("#stack-table", DataTable)
        stack.add_columns("depth", "function", "line")
        stack.zebra_stripes = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "run":
            self.action_run_trace()
        elif event.button.id == "prev":
            self.action_previous_step()
        elif event.button.id == "next":
            self.action_next_step()

    def action_run_trace(self) -> None:
        """Run the code from the editor and render the first trace step."""
        editor = self.query_one("#code-input", TextArea)
        self._result = self._runner.run(editor.text)
        self._current_step_index = 0
        self._render_current_step()

    def action_next_step(self) -> None:
        """Move to the next trace step."""
        if self._result is None or not self._result.steps:
            self.action_run_trace()
            return
        self._current_step_index = min(
            self._current_step_index + 1,
            len(self._result.steps) - 1,
        )
        self._render_current_step()

    def action_previous_step(self) -> None:
        """Move to the previous trace step."""
        if self._result is None or not self._result.steps:
            return
        self._current_step_index = max(self._current_step_index - 1, 0)
        self._render_current_step()

    def _render_current_step(self) -> None:
        """Refresh all panels for the selected step."""
        if self._result is None or not self._result.steps:
            self._set_status("No trace yet. Press Run.")
            return

        step = self._result.steps[self._current_step_index]
        self._render_source(step)
        self._render_variables(step)
        self._render_stack(step.call_stack)
        self._render_explanation(step)

        total = len(self._result.steps)
        status = f"Step {step.index + 1}/{total} | event={step.event.value}"
        if self._result.exception is not None:
            status += (
                f" | final error: {self._result.exception.type_name}: "
                f"{self._result.exception.message}"
            )
        self._set_status(status)

    def _render_source(self, step: TraceStep) -> None:
        """Render source code and highlight the current line."""
        source_view = self.query_one("#source-view", RichLog)
        source_view.clear()

        if self._result is None:
            return

        current_line = step.line_number
        for number, line in enumerate(self._result.source_lines, start=1):
            prefix = "▶" if number == current_line else " "
            text = Text(f"{prefix} {number:>3} | {line}")
            if number == current_line:
                text.stylize("bold reverse")
            source_view.write(text)

    def _render_variables(self, step: TraceStep) -> None:
        """Render local variables from every visible frame."""
        table = self.query_one("#variables-table", DataTable)
        table.clear(columns=False)

        for frame in step.call_stack:
            if not frame.local_variables:
                table.add_row(frame.function_name, "—", "—", "—")
                continue
            for variable in frame.local_variables:
                table.add_row(
                    frame.function_name,
                    variable.name,
                    variable.type_name,
                    variable.value_repr,
                )

    def _render_stack(self, frames: tuple[FrameSnapshot, ...]) -> None:
        """Render the current call stack."""
        table = self.query_one("#stack-table", DataTable)
        table.clear(columns=False)

        for depth, frame in enumerate(frames):
            table.add_row(str(depth), frame.function_name, str(frame.line_number))

    def _render_explanation(self, step: TraceStep) -> None:
        """Render explanation, return value, exception and stdout."""
        log = self.query_one("#explanation-log", RichLog)
        log.clear()
        log.write(self._explainer.explain(step))

        if step.return_value_repr is not None:
            log.write(f"Return value: {step.return_value_repr}")

        if step.exception is not None:
            log.write(
                f"Exception: {step.exception.type_name}: {step.exception.message}"
            )

        if step.stdout:
            log.write("\nstdout:")
            log.write(step.stdout.rstrip())

    def _set_status(self, message: str) -> None:
        """Update the status label."""
        self.query_one("#status", Label).update(message)


def run_app(path: Path | None = None) -> None:
    """Start TraceTutor, optionally loading initial code from a file."""
    initial_code = DEFAULT_CODE
    if path is not None:
        initial_code = path.read_text(encoding="utf-8")
    TraceTutorApp(initial_code).run()
