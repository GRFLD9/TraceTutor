"""Built-in educational lessons for TraceTutor."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Lesson:
    """A small Python example prepared for educational tracing."""

    slug: str
    title: str
    description: str
    code: str
    focus_variable: str | None = None


LESSONS: tuple[Lesson, ...] = (
    Lesson(
        slug="state_changes",
        title="State changes",
        description="Shows how one variable changes during sequential execution.",
        code="""x = 1
print(x)

x = 2
print(x)

x = 2
print(x)

x = 3
print(x)
""",
        focus_variable="x",
    ),
    Lesson(
        slug="loop_sum",
        title="Loop sum",
        description="Shows how a loop updates an accumulator variable.",
        code="""total = 0

for number in range(1, 5):
    total = total + number
    print(total)

result = total
""",
        focus_variable="total",
    ),
    Lesson(
        slug="function_call",
        title="Function call",
        description="Shows entering a function, local variables and return value.",
        code="""def add(a, b):
    result = a + b
    return result

answer = add(2, 3)
print(answer)
""",
        focus_variable="result",
    ),
    Lesson(
        slug="exception",
        title="Exception",
        description="Shows where a runtime exception appears in the trace.",
        code="""x = 10
y = 0

result = x / y
print(result)
""",
        focus_variable="result",
    ),
)


def list_lessons() -> tuple[Lesson, ...]:
    """Return all built-in lessons."""
    return LESSONS


def get_lesson(slug: str) -> Lesson:
    """Return a lesson by its slug."""
    for lesson in LESSONS:
        if lesson.slug == slug:
            return lesson
    raise KeyError(f"Unknown lesson slug: {slug}")


def default_lesson() -> Lesson:
    """Return the lesson shown when TraceTutor starts."""
    return get_lesson("loop_sum")
