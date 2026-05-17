"""Profile TraceTutor core tracing performance."""

from __future__ import annotations

import cProfile
import pstats
from pathlib import Path
from textwrap import dedent

from tracetutor.runner import CodeRunner
from tracetutor.timeline import VariableTimelineBuilder

PROFILE_DIR = Path("docs")
PROFILE_OUTPUT = PROFILE_DIR / "profile_stats.txt"

REPEAT_COUNT = 50

EXAMPLES = {
    "many_assignments": "\n".join(
        ["x = 0"]
        + [f"x = x + {number}" for number in range(1, 120)]
        + ["print(x)"]
    ),
    "loop_sum": dedent(
        """
        total = 0

        for number in range(1, 200):
            total = total + number

        result = total
        print(result)
        """
    ),
    "function_calls": dedent(
        """
        def add(a, b):
            result = a + b
            return result

        total = 0

        for number in range(120):
            total = add(total, number)

        print(total)
        """
    ),
    "nested_calls": dedent(
        """
        def square(x):
            result = x * x
            return result

        def sum_squares(limit):
            total = 0
            for number in range(limit):
                total = total + square(number)
            return total

        answer = sum_squares(80)
        print(answer)
        """
    ),
    "recursion": dedent(
        """
        def factorial(n):
            if n <= 1:
                return 1
            return n * factorial(n - 1)

        answer = factorial(10)
        print(answer)
        """
    ),
    "list_state": dedent(
        """
        values = []
        total = 0

        for number in range(60):
            values.append(number)
            total = total + number

        print(total)
        """
    ),
}


def profile_runner() -> None:
    """Run the main tracing pipeline many times."""
    runner = CodeRunner(max_steps=20_000)

    for _ in range(REPEAT_COUNT):
        for code in EXAMPLES.values():
            result = runner.run(code)
            if not result.steps:
                raise RuntimeError("TraceTutor produced an empty trace")


def profile_timeline() -> None:
    """Build variable timelines for larger traces."""
    runner = CodeRunner(max_steps=20_000)

    loop_result = runner.run(EXAMPLES["loop_sum"])
    call_result = runner.run(EXAMPLES["function_calls"])
    list_result = runner.run(EXAMPLES["list_state"])

    for _ in range(REPEAT_COUNT * 10):
        VariableTimelineBuilder.build(
            loop_result,
            frame_depth=0,
            function_name="<module>",
            variable_name="total",
        )
        VariableTimelineBuilder.build(
            call_result,
            frame_depth=0,
            function_name="<module>",
            variable_name="total",
        )
        VariableTimelineBuilder.build(
            list_result,
            frame_depth=0,
            function_name="<module>",
            variable_name="total",
        )


def run_profile() -> None:
    """Run profiling for tracing and timeline building."""
    PROFILE_DIR.mkdir(exist_ok=True)

    profiler = cProfile.Profile()
    profiler.enable()

    profile_runner()
    profile_timeline()

    profiler.disable()

    with PROFILE_OUTPUT.open("w", encoding="utf-8") as output:
        stats = pstats.Stats(profiler, stream=output)
        stats.strip_dirs()
        stats.sort_stats("cumtime")
        stats.print_stats(40)


if __name__ == "__main__":
    run_profile()
