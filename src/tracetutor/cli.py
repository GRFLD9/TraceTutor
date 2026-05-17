"""Command-line entry point for TraceTutor."""

import argparse
from pathlib import Path

from tracetutor.renderer import run_app


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="tracetutor",
        description="Interactive visualizer of Python code execution traces.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        help="Optional Python file to load into the editor.",
    )
    return parser


def main() -> None:
    """Parse CLI arguments and run the Textual app."""
    args = build_parser().parse_args()
    run_app(args.file)
