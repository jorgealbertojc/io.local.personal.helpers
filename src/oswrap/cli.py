# PYTHON_ARGCOMPLETE_OK
"""Entry point for the os command.

Dispatches the user-supplied arguments to the appropriate command
module through the registry exposed by oswrap.commands. This module
owns argument parsing only; the actual work lives in the command
modules.
"""
import sys
from argparse import ArgumentParser

import argcomplete

from oswrap.commands import COMMANDS, resolve, summaries
from oswrap.helptext import show_general_help
from oswrap.lib.sudo import invalidate_sudo_timestamp

_EXIT_OK = 0
_EXIT_FAILURE = 1
_EXIT_USAGE = 2

_HELP_FLAGS = frozenset({"help", "--help", "-h"})
_VERBOSE_FLAGS = frozenset({"-v", "--verbose"})


def _build_completion_parser() -> ArgumentParser:
    """Build an argparse parser used exclusively for shell completion.

    This parser is never used for actual argument dispatch. It exists
    solely so that argcomplete can enumerate the available commands,
    aliases, and global flags when the user presses TAB. Keeping it
    separate from the manual dispatch logic in main() avoids forcing
    a full argparse migration before the CLI has enough commands to
    justify one.
    """
    parser = ArgumentParser(prog="os", add_help=False)
    subparsers = parser.add_subparsers(dest="command")

    for spec in COMMANDS.values():
        for name in (spec.name, *spec.aliases):
            sub = subparsers.add_parser(name, add_help=False)
            sub.add_argument("-v", "--verbose", action="store_true")
            sub.add_argument("--help", "-h", action="store_true")

    return parser


def main() -> int:
    """Run the os command and return a process exit code.

    Exit codes:
        0: The command completed successfully, or help was printed
            after an explicit help request.
        1: The command ran but failed (returned by the command's run
            callable).
        2: Usage error: no arguments were provided, or the requested
            command is not registered.
    """
    argcomplete.autocomplete(_build_completion_parser())

    args = sys.argv[1:]

    if not args:
        show_general_help(summaries())
        return _EXIT_USAGE

    head, *rest = args

    if head in _HELP_FLAGS:
        show_general_help(summaries())
        return _EXIT_OK

    spec = resolve(head)
    if spec is None:
        print(f"Error: unknown command '{head}'.", file=sys.stderr)
        print(file=sys.stderr)
        show_general_help(summaries())
        return _EXIT_USAGE

    if any(arg in _HELP_FLAGS for arg in rest):
        spec.help()
        return _EXIT_OK

    verbose = any(arg in _VERBOSE_FLAGS for arg in rest)
    try:
        return spec.run(verbose=verbose)
    finally:
        invalidate_sudo_timestamp()


if __name__ == "__main__":
    sys.exit(main())
