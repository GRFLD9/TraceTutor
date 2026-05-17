from tracetutor.runner import CodeRunner
from tracetutor.state import EventKind


def test_runner_captures_stdout_and_variables() -> None:
    result = CodeRunner().run("x = 2\ny = x + 3\nprint(y)\n")

    assert result.is_success
    assert result.stdout.strip() == "5"
    assert any(step.event == EventKind.LINE for step in result.steps)
    assert any(
        variable.name == "x" and variable.value_repr == "2"
        for step in result.steps
        for frame in step.call_stack
        for variable in frame.local_variables
    )


def test_runner_captures_function_call_and_return() -> None:
    code = """def add(a, b):
        result = a + b
        return result

value = add(2, 3)"""
    result = CodeRunner().run(code)

    assert result.is_success
    assert any(step.event == EventKind.CALL for step in result.steps)
    assert any(
        step.event == EventKind.RETURN and step.return_value_repr == "5"
        for step in result.steps
    )


def test_runner_reports_runtime_exception() -> None:
    result = CodeRunner().run("x = 1\ny = x / 0\n")

    assert not result.is_success
    assert result.exception is not None
    assert result.exception.type_name == "ZeroDivisionError"
    assert result.exception.line_number == 2
    assert any(step.event == EventKind.EXCEPTION for step in result.steps)


def test_runner_reports_syntax_error() -> None:
    result = CodeRunner().run("def broken(:\n    pass\n")

    assert not result.is_success
    assert result.exception is not None
    assert result.exception.type_name == "SyntaxError"
    assert result.steps[0].event == EventKind.EXCEPTION


def test_runner_reports_empty_code() -> None:
    result = CodeRunner().run("   \n")

    assert not result.is_success
    assert result.exception is not None
    assert result.exception.type_name == "EmptyCodeError"
