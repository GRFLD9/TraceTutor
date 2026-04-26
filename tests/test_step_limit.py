from tracetutor.runner import CodeRunner


def test_runner_stops_infinite_loop_by_step_limit() -> None:
    result = CodeRunner(max_steps=10).run("while True:\n    pass\n")

    assert not result.is_success
    assert result.exception is not None
    assert result.exception.type_name == "StepLimitExceeded"
