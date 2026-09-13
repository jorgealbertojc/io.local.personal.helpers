"""General help output for the os command.

This module is responsible only for presenting the top-level usage
message. Command-specific help lives inside each command module
under oswrap.commands and is dispatched from oswrap.cli.
"""


def show_general_help(commands: dict[str, str]) -> None:
    """Print the general help message for the os command.

    Args:
        commands: Mapping of command name to a one-line summary. The
            caller (oswrap.cli) builds this from the command registry
            so that this module stays free of any compile-time
            dependency on oswrap.commands.
    """
    print("os - System helper command")
    print()
    print("Description:")
    print("  The 'os' command is an entry point to manage basic")
    print("  system administration tasks on Ubuntu 24.04 LTS.")
    print()
    print("Usage:")
    print("  os")
    print("  os help")
    print("  os --help")
    print("  os <command> [options]")
    print()
    print("Commands:")
    if commands:
        width = max(len(name) for name in commands)
        for name, summary in commands.items():
            print(f"  {name:<{width}}  {summary}")
    else:
        print("  (no commands registered yet)")
    print()
    print("Options:")
    print("  help, --help, -h  Show this help message.")
    print("  -v, --verbose     Print full command output to the terminal")
    print("                    while still writing it to the execution log.")
    print()
    print("Notes:")
    print("  This tool is under development and will be extended with more")
    print("  system management capabilities.")
