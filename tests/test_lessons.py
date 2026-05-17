"""Tests for built-in educational lessons."""

import pytest

from tracetutor.lessons import default_lesson, get_lesson, list_lessons
from tracetutor.runner import CodeRunner


def test_lessons_are_not_empty() -> None:
    """Built-in lessons should contain runnable code and descriptions."""
    lessons = list_lessons()

    assert lessons
    for lesson in lessons:
        assert lesson.slug
        assert lesson.title
        assert lesson.description
        assert lesson.code.strip()


@pytest.mark.parametrize("slug", [lesson.slug for lesson in list_lessons()])
def test_each_lesson_can_be_traced(slug: str) -> None:
    """Each lesson should produce at least one trace step."""
    lesson = get_lesson(slug)
    result = CodeRunner().run(lesson.code)

    assert result.steps


def test_default_lesson_is_loop_sum() -> None:
    """Default lesson should be the loop accumulator example."""
    lesson = default_lesson()

    assert lesson.slug == "loop_sum"
    assert lesson.focus_variable == "total"


def test_unknown_lesson_raises_key_error() -> None:
    """Unknown lesson slugs should fail explicitly."""
    with pytest.raises(KeyError):
        get_lesson("unknown")
