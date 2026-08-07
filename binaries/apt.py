#!/usr/bin/env python3

import datetime
import getpass
import os
import subprocess
import sys
import uuid
from typing import List, Tuple


def _is_sudo_member() -> bool:
    """Return True if the current user is root or belongs to the sudo group."""
    try:
        result = subprocess.run(
            ["id", "-nG"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

    groups = set(result.stdout.split())
    return os.getuid() == 0 or "sudo" in groups


def run_apt_update() -> int:
    """Perform `apt update`, list upgradable packages and then run `apt upgrade`.

    The sudo password is requested once and reused for both update and upgrade.
    All output is logged to a file; only errors are displayed to the user.
    """
    # Initialize execution context: UUID and log file
    execution_uuid = str(uuid.uuid4())
    timestamp = datetime.datetime.now().strftime("%s.%f")[:-3]  # millisecond precision
    log_filename = f"{timestamp}-{execution_uuid}-os-update.log"
    log_filepath = os.path.join("/tmp", log_filename)

    try:
        log_file = open(log_filepath, "w", buffering=1)
    except Exception as e:
        print(f"Error: could not create log file {log_filepath}: {e}", file=sys.stderr)
        return 1

    if not _is_sudo_member():
        print("Error: current user is not in the sudo group.", file=sys.stderr)
        log_file.close()
        return 1

    print("Checking sudo credentials...")
    password = getpass.getpass("Sudo password: ")
    if not password:
        print("Error: password cannot be empty.", file=sys.stderr)
        log_file.close()
        return 1

    # Run apt update (requires sudo). Use a helper that streams output and
    # writes the sudo password once to stdin. Set DEBIAN_FRONTEND to
    # noninteractive and pass Dpkg options during upgrade to avoid prompts.
    print("Updating package repositories...")
    update_cmd = [
        "sudo",
        "-S",
        "-p",
        "",
        "env",
        "DEBIAN_FRONTEND=noninteractive",
        "apt",
        "-o",
        "Apt::Cmd::Disable-Script-Warning=true",
        "-y",
        "update",
        "--fix-missing",
    ]

    rc = _run_sudo_and_stream(password, update_cmd, log_file)
    if rc != 0:
        log_file.write("Error: apt update failed. The upgrade workflow was aborted.\n")
        print(f"Error: apt update failed. See log: {log_filepath}", file=sys.stderr)
        try:
            with open(log_filepath, "r") as f:
                print(f.read(), file=sys.stderr)
        except Exception:
            pass
        try:
            log_file.close()
        except Exception:
            pass
        return rc

    # After running `apt update`, check which packages are upgradable.
    try:
        upg = _get_upgradable_packages()
    except Exception as exc:
        print(f"Warning: could not obtain upgradable packages list: {exc}", file=sys.stderr)
        # proceed to attempt upgrade even if listing failed
        upg = []

    if not upg:
        log_file.write("No upgrades available.\n")
    else:
        log_file.write("Packages scheduled for upgrade:\n")
        for pkg in upg:
            log_file.write(f"  - {pkg}\n")

    # Proceed to run apt upgrade using the same sudo password.
    print("Running system upgrade...")
    # Include Dpkg options to avoid interactive config prompts and run noninteractive.
    upgrade_cmd = [
        "sudo",
        "-S",
        "-p",
        "",
        "env",
        "DEBIAN_FRONTEND=noninteractive",
        "apt",
        "-o",
        "Apt::Cmd::Disable-Script-Warning=true",
        "-o",
        "APT::Get::Always-Include-Phased-Updates=true",
        "-o",
        "Dpkg::Options::=--force-confdef",
        "-o",
        "Dpkg::Options::=--force-confold",
        "-y",
        "upgrade",
        "--fix-missing",
        "--fix-broken",
    ]

    rc_upgrade, upgrade_output = _run_sudo_and_stream(password, upgrade_cmd, log_file, capture_output=True)

    should_link_ffmpeg = rc_upgrade == 0 and _upgrade_installed_packages(upgrade_output)
    if should_link_ffmpeg:
        print("Configuring Opera ffmpeg library...")
        opera_link_cmd = [
            "sudo",
            "-S",
            "-p",
            "",
            "ln",
            "-vsf",
            "/snap/chromium/current/usr/lib/chromium-browser/libffmpeg.so",
            "/usr/lib/x86_64-linux-gnu/opera-stable/libffmpeg.so",
        ]
        rc_link, _ = _run_sudo_and_stream(password, opera_link_cmd, log_file)
        if rc_link != 0:
            log_file.write("Warning: Opera ffmpeg link command failed.\n")

    # Clear password variable as soon as possible
    password = None
    try:
        del password
    except Exception:
        pass

    if rc_upgrade != 0:
        print(f"Error: apt upgrade failed. See log: {log_filepath}", file=sys.stderr)
        try:
            with open(log_filepath, "r") as f:
                print(f.read(), file=sys.stderr)
        except Exception:
            pass
    else:
        print("Update completed successfully.")

    try:
        log_file.close()
    except Exception:
        pass

    return rc_upgrade


def _run_sudo_and_stream(password: str, argv: list, log_file=None, capture_output: bool = False) -> Tuple[int, str]:
    """Run a sudo command (argv) sending the password once and logging
    stdout/stderr to log_file. Returns (returncode, output).
    """
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
    except FileNotFoundError:
        print("Error: 'sudo' command not found.", file=sys.stderr)
        return 1, ""

    try:
        proc.stdin.write(f"{password}\n")
        proc.stdin.flush()
        proc.stdin.close()
    except Exception:
        pass

    output_lines: List[str] = []
    try:
        for line in proc.stdout:
            if log_file:
                log_file.write(line)
            if capture_output:
                output_lines.append(line)
    except Exception:
        try:
            out, _ = proc.communicate(timeout=10)
            if out:
                if log_file:
                    log_file.write(out)
                if capture_output:
                    output_lines.append(out)
        except Exception:
            pass

    proc.wait()
    return proc.returncode, "".join(output_lines)


def _get_upgradable_packages() -> List[str]:
    """Run `apt list --upgradable` and return a deduplicated list of package names."""
    try:
        res = subprocess.run(
            [
                "apt",
                "-o",
                "APT::Get::Always-Include-Phased-Updates=true",
                "list",
                "--upgradable",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return []

    packages: List[str] = []
    seen = set()
    for line in res.stdout.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("listing"):
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        pkg_repo = parts[0]
        pkg_name = pkg_repo.split("/")[0]
        if pkg_name and pkg_name not in seen:
            seen.add(pkg_name)
            packages.append(pkg_name)

    return packages


def _upgrade_installed_packages(output: str) -> bool:
    """Return True if apt upgrade output indicates packages were installed or upgraded."""
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        if " upgraded, " in line and " newly installed, " in line and " to remove" in line:
            parts = [part.strip() for part in line.split(",")]
            if len(parts) >= 3:
                try:
                    upgraded = int(parts[0].split()[0])
                    newly_installed = int(parts[1].split()[0])
                    removed = int(parts[2].split()[0])
                except ValueError:
                    continue
                return upgraded > 0 or newly_installed > 0 or removed > 0
    return False
