"""Textual-based interface for TraceTutor."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, HorizontalScroll, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Label, RichLog, Static, TextArea

from tracetutor.explanations import ExplainerProtocol, StepExplainer
from tracetutor.runner import CodeRunner
from tracetutor.state import FrameSnapshot, TraceResult, TraceStep
from tracetutor.timeline import VariableTimelineBuilder

DEFAULT_CODE = """total = 0

for number in range(1, 5):
    total = total + number
    print(total)

result = total
"""


@dataclass(frozen=True, slots=True)
class VariableSelection:
    """Selected variable identity in the current variable table."""

    frame_depth: int
    function_name: str
    variable_name: str


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
    
    #timeline-title {
    height: 1;
    }
    
    #timeline-scroll {
        height: 4;
        border: round $primary;
        margin-bottom: 0;
    }
    
    #timeline-scale {
        width: auto;
        height: 1;
    }
    
    #timeline-help {
        height: 1;
        content-align: left middle;
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
        self._explainer: ExplainerProtocol = StepExplainer()
        self._result: TraceResult | None = None
        self._current_step_index = 0
        self._selected_variable: VariableSelection | None = None
        self._variable_rows: dict[str, VariableSelection] = {}

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
                yield Label("Variable timeline")
                yield Label("", id="timeline-title")
                with HorizontalScroll(id="timeline-scroll"):
                    yield Static("", id="timeline-scale")
                yield Label("* means that the variable value changed on this step.", id="timeline-help")
        yield Footer()

    def on_mount(self) -> None:
        """Prepare tables when the app starts."""
        variables = self.query_one("#variables-table", DataTable)
        variables.add_columns("frame", "name", "type", "value")
        variables.zebra_stripes = True
        variables.cursor_type = "row"

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

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Show a timeline for the selected variable row."""
        if event.data_table.id != "variables-table":
            return

        row_key = event.row_key.value
        if row_key is None:
            return

        selection = self._variable_rows.get(row_key)
        if selection is None:
            return

        self._selected_variable = selection
        self._render_timeline()

    def action_run_trace(self) -> None:
        """Run the code from the editor and render the first trace step."""
        editor = self.query_one("#code-input", TextArea)
        self._result = self._runner.run(editor.text)
        self._current_step_index = 0
        self._selected_variable = None
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
        self._render_timeline()

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
        self._variable_rows.clear()

        for frame_depth, frame in enumerate(step.call_stack):
            if not frame.local_variables:
                table.add_row(frame.function_name, "—", "—", "—")
                continue

            for variable in frame.local_variables:
                row_key = (
                    f"{frame_depth}:{frame.function_name}:"
                    f"{variable.name}:{len(self._variable_rows)}"
                )
                self._variable_rows[row_key] = VariableSelection(
                    frame_depth=frame_depth,
                    function_name=frame.function_name,
                    variable_name=variable.name,
                )
                table.add_row(
                    frame.function_name,
                    variable.name,
                    variable.type_name,
                    variable.value_repr,
                    key=row_key,
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

    def _render_timeline(self) -> None:
        """Render a horizontal timeline for the selected variable."""
        title = self.query_one("#timeline-title", Label)
        scale_view = self.query_one("#timeline-scale", Static)
        help_label = self.query_one("#timeline-help", Label)

        title.update("")
        scale_view.update("")
        help_label.update("* means that the variable value changed on this step.")

        if self._result is None:
            title.update("Run code to build a variable timeline.")
            return

        if self._selected_variable is None:
            title.update("Select a variable row to show its timeline.")
            return

        selection = self._selected_variable
        points = VariableTimelineBuilder.build(
            self._result,
            frame_depth=selection.frame_depth,
            function_name=selection.function_name,
            variable_name=selection.variable_name,
        )

        title.update(
            f"Timeline for `{selection.variable_name}` "
            f"in `{selection.function_name}` "
            f"(frame depth {selection.frame_depth}):"
        )

        visible_points = tuple(
            point
            for point in points
            if point.step_index <= self._current_step_index
        )

        if not visible_points:
            scale_view.update("No values found up to the current step.")
            return

        scale = Text()

        for index, point in enumerate(visible_points):
            if index > 0:
                scale.append("──", style="dim")

            is_current = point.step_index == self._current_step_index
            step_number = point.step_index + 1
            changed_marker = "*" if point.changed else " "

            cell = (
                f"[{changed_marker}{step_number}: "
                f"{selection.variable_name}={point.value_repr}]"
            )

            if point.changed and is_current:
                scale.append(cell, style="bold black on yellow")
            elif point.changed:
                scale.append(cell, style="bold black on green")
            elif is_current:
                scale.append(cell, style="bold reverse")
            else:
                scale.append(cell)

        scale_view.update(scale)
        self.call_after_refresh(self._scroll_timeline_to_end)

    def _scroll_timeline_to_end(self) -> None:
        """Scroll the variable timeline to the newest visible cell."""
        timeline_scroll = self.query_one("#timeline-scroll", HorizontalScroll)
        timeline_scroll.scroll_to(
            x=timeline_scroll.max_scroll_x,
            y=0,
            animate=False,
        )

    def _set_status(self, message: str) -> None:
        """Update the status label."""
        self.query_one("#status", Label).update(message)


def run_app(path: Path | None = None) -> None:
    """Start TraceTutor, optionally loading initial code from a file."""
    initial_code = DEFAULT_CODE
    if path is not None:
        initial_code = path.read_text(encoding="utf-8")
    TraceTutorApp(initial_code).run()
