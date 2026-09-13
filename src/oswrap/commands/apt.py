"""The `os update` command: apt update followed by apt upgrade.

Implements the apt-based system update workflow exposed through
`os update`. The flow is:

1. Verify the current user can escalate with sudo.
2. Prompt for the sudo password once.
3. Run `apt update` non-interactively.
4. List the packages that are upgradable.
5. Run `apt upgrade` non-interactively, reusing the same password.
6. If any package was actually changed, refresh the Opera ffmpeg
   shared library symlink.

All subprocess output is written to a log file under /tmp. Failures
dump the log to stderr so the user can diagnose the problem without
digging through the filesystem.
"""

import subprocess
import sys
from pathlib import Path

from oswrap.lib.logs import ExecutionLog
from oswrap.lib.sudo import (
    is_sudo_member,
    prompt_password,
    run_sudo_and_stream,
)


def show_help() -> None:
    """Print help specific to the `os update` command."""
    print("os update - Update apt repositories and upgrade packages")
    print()
    print("Description:")
    print("  Runs 'apt update' to refresh the package index, lists the")
    print("  upgradable packages, then runs 'apt upgrade' to install the")
    print("  available updates. Both steps run non-interactively and")
    print("  reuse a single sudo authentication.")
    print()
    print("Usage:")
    print("  os update [-v | --verbose]")
    print()
    print("Options:")
    print("  -v, --verbose  Print full command output to the terminal")
    print("                 while still writing it to the execution log.")
    print()
    print("Notes:")
    print("  Requires the current user to be root or a member of the")
    print("  sudo group. The sudo password is requested once and reused")
    print("  for the whole workflow.")


def run_apt_update(verbose: bool = False) -> int:
    """Run `apt update` followed by `apt upgrade`.

    Args:
        verbose: When True, mirror subprocess output to the terminal
            in addition to the log file.

    Returns:
        The exit code of the `apt upgrade` step. Non-zero values are
        also returned by earlier aborting conditions: the user is not
        in the sudo group, the password is empty, or `apt update`
        failed.
    """
    with ExecutionLog("os-update") as log:
        if not is_sudo_member():
            print(
                "Error: current user is not in the sudo group.",
                file=sys.stderr,
            )
            return 1

        print("Checking sudo credentials...")
        password = prompt_password()
        if password is None:
            print("Error: password cannot be empty.", file=sys.stderr)
            return 1

        print("Updating package repositories...")
        update_cmd = [
            "sudo", "-S", "-p", "",
            "env", "DEBIAN_FRONTEND=noninteractive",
            "apt",
            "-o", "Apt::Cmd::Disable-Script-Warning=true",
            "-y",
            "update",
        ]
        rc_update, _ = run_sudo_and_stream(
            password, update_cmd, log=log, verbose=verbose
        )
        if rc_update != 0:
            log.write("Error: apt update failed. Upgrade aborted.\n")
            _report_failure("apt update failed", log.path)
            return rc_update

        upgradable = _list_upgradable_packages()
        if upgradable:
            log.write("Packages scheduled for upgrade:\n")
            for pkg in upgradable:
                log.write(f"  - {pkg}\n")
        else:
            log.write("No upgrades available.\n")

        print("Running system upgrade...")
        upgrade_cmd = [
            "sudo", "-S", "-p", "",
            "env", "DEBIAN_FRONTEND=noninteractive",
            "apt",
            "-o", "Apt::Cmd::Disable-Script-Warning=true",
            "-o", "APT::Get::Always-Include-Phased-Updates=true",
            "-o", "Dpkg::Options::=--force-confdef",
            "-o", "Dpkg::Options::=--force-confold",
            "-y",
            "upgrade",
            "--fix-missing",
            "--fix-broken",
        ]
        rc_upgrade, upgrade_output = run_sudo_and_stream(
            password,
            upgrade_cmd,
            log=log,
            capture_output=True,
            verbose=verbose,
        )

        if rc_upgrade == 0 and _packages_were_changed(upgrade_output):
            print("Configuring Opera ffmpeg library...")
            _link_opera_ffmpeg(password, log, verbose=verbose)

        if rc_upgrade != 0:
            _report_failure("apt upgrade failed", log.path)
            return rc_upgrade

        print("Update completed successfully.")
        return 0


def _list_upgradable_packages() -> list[str]:
    """Return the package names reported by `apt list --upgradable`."""
    try:
        result = subprocess.run(
            [
                "apt",
                "-o", "APT::Get::Always-Include-Phased-Updates=true",
                "list", "--upgradable",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return []

    packages: list[str] = []
    seen: set[str] = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("listing"):
            continue

        parts = line.split()
        if not parts:
            continue

        pkg_name = parts[0].split("/")[0]
        if pkg_name and pkg_name not in seen:
            seen.add(pkg_name)
            packages.append(pkg_name)

    return packages


def _packages_were_changed(output: str) -> bool:
    """Return True when apt's summary line reports any change.

    Looks for the standard English summary line::

        N upgraded, M newly installed, K to remove and J not upgraded.

    and returns True when any of the first three counters is greater
    than zero.
    """
    for line in output.splitlines():
        stripped = line.strip()
        if (
            " upgraded, " not in stripped
            or " newly installed, " not in stripped
            or " to remove" not in stripped
        ):
            continue

        parts = [part.strip() for part in stripped.split(",")]
        if len(parts) < 3:
            continue

        try:
            upgraded = int(parts[0].split()[0])
            newly_installed = int(parts[1].split()[0])
            removed = int(parts[2].split()[0])
        except (ValueError, IndexError):
            continue

        return upgraded > 0 or newly_installed > 0 or removed > 0

    return False


def _link_opera_ffmpeg(
    password: str,
    log: ExecutionLog,
    verbose: bool = False,
) -> None:
    """Recreate the Opera ffmpeg shared library symlink.

    Snap-installed Chromium places its libffmpeg.so at a path that
    cannot be discovered reliably at runtime, so the source path is
    hardcoded. A failure here is logged as a warning and does not
    abort the update workflow.
    """
    link_cmd = [
        "sudo", "-S", "-p", "",
        "ln", "-vsf",
        "/snap/chromium/current/usr/lib/chromium-browser/libffmpeg.so",
        "/usr/lib/x86_64-linux-gnu/opera-stable/libffmpeg.so",
    ]
    rc, _ = run_sudo_and_stream(password, link_cmd, log=log, verbose=verbose)
    if rc != 0:
        log.write("Warning: Opera ffmpeg link command failed.\n")


def _report_failure(message: str, log_path: Path) -> None:
    """Print a failure message and dump the log to stderr."""
    print(f"Error: {message}. See log: {log_path}", file=sys.stderr)
    try:
        print(log_path.read_text(encoding="utf-8"), file=sys.stderr)
    except OSError:
        pass
