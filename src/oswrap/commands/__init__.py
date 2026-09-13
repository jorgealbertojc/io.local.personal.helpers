"""Command registry for the os entry point.

Each command lives in its own module under oswrap.commands and
exposes two public callables:

- ``run_<name>(...) -> int``: executes the command and returns a
  process exit code.
- ``show_help() -> None``: prints command-specific help.

This package aggregates those modules into a single registry.
oswrap.cli uses it for dispatch, and oswrap.helptext consumes the
name -> summary mapping through :func:`summaries`.
"""

from collections.abc import Callable
from dataclasses import dataclass

from oswrap.commands import apt


@dataclass(frozen=True)
class CommandSpec:
    """Metadata and entry points for a single command.

    Attributes:
        name: Canonical command name, as typed after ``os``.
        summary: One-line description shown in the general help.
        run: Callable invoked to execute the command. Signature is
            command-specific; cli.py is responsible for passing the
            right arguments.
        help: Callable that prints the command-specific help message.
        aliases: Alternative names accepted for this command.
    """

    name: str
    summary: str
    run: Callable[..., int]
    help: Callable[[], None]
    aliases: tuple[str, ...] = ()


COMMANDS: dict[str, CommandSpec] = {
    "update": CommandSpec(
        name="update",
        summary="Refresh the apt index and upgrade installed packages.",
        run=apt.run_apt_update,
        help=apt.show_help,
        aliases=("apt-update",),
    ),
}


def resolve(name: str) -> CommandSpec | None:
    """Return the spec for ``name``, matching canonical or alias names."""
    if name in COMMANDS:
        return COMMANDS[name]
    for spec in COMMANDS.values():
        if name in spec.aliases:
            return spec
    return None


def summaries() -> dict[str, str]:
    """Return a name -> summary mapping for the general help output."""
    return {spec.name: spec.summary for spec in COMMANDS.values()}
