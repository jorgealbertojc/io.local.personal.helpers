"""Sudo helpers for oswrap commands.

Encapsulates everything required to run privileged commands:
sudo-group membership checks, secure password prompting, and a
streaming runner that feeds the password once to sudo's stdin and
mirrors output to an ExecutionLog.
"""

import getpass
import os
import subprocess
import sys

from oswrap.lib.logs import ExecutionLog


def is_sudo_member() -> bool:
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


def prompt_password() -> str | None:
    """Prompt the user for a sudo password.

    Returns the entered password, or None when the user submits an
    empty string (in which case the caller must abort the privileged
    operation).
    """
    return getpass.getpass("Sudo password: ") or None


def run_sudo_and_stream(
    password: str,
    argv: list[str],
    log: ExecutionLog | None = None,
    capture_output: bool = False,
    verbose: bool = False,
) -> tuple[int, str]:
    """Run a sudo command, feeding the password once and streaming output.

    The password is written to the child process's stdin immediately
    after it is spawned, then stdin is closed. ``sudo -S -p ""`` (which
    the caller is expected to include in ``argv``) reads the password
    from stdin and suppresses the interactive prompt.

    Output is always merged (stderr redirected into stdout). Each line
    is written to ``log`` when provided, echoed to the terminal when
    ``verbose`` is True, and accumulated into the returned string when
    ``capture_output`` is True.

    Args:
        password: The sudo password, without a trailing newline.
        argv: Full command line to execute, including ``sudo`` and any
            flags such as ``-S -p ""``.
        log: Optional ExecutionLog where output is persisted.
        capture_output: When True, accumulate output and return it.
        verbose: When True, mirror output to stdout as it arrives.

    Returns:
        A tuple of (returncode, captured_output). ``captured_output``
        is empty when ``capture_output`` is False.
    """
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        print("Error: 'sudo' command not found.", file=sys.stderr)
        return 1, ""

    # Feed the password once. If sudo has cached credentials (NOPASSWD
    # or an active timestamp), the write may fail with BrokenPipeError;
    # that is fine and intentionally swallowed.
    if proc.stdin is not None:
        try:
            proc.stdin.write(f"{password}\n")
            proc.stdin.flush()
            proc.stdin.close()
        except OSError:
            pass

    output_lines: list[str] = []
    if proc.stdout is not None:
        try:
            for line in proc.stdout:
                if log is not None:
                    log.write(line)
                if verbose:
                    print(line, end="")
                if capture_output:
                    output_lines.append(line)
        except OSError:
            try:
                out, _ = proc.communicate(timeout=10)
                if out:
                    if log is not None:
                        log.write(out)
                    if capture_output:
                        output_lines.append(out)
            except OSError:
                pass

    proc.wait()
    return proc.returncode, "".join(output_lines)

def invalidate_sudo_timestamp() -> None:
    """Invalidate the cached sudo timestamp for the current user.

    Forces the next sudo invocation to prompt for a password again.
    Safe to call even when no timestamp exists; errors are swallowed.
    Uses ``sudo -k`` (current terminal/user only), not ``sudo -K``
    (which would invalidate timestamps for all of the user's sessions).
    """
    try:
        subprocess.run(
            ["sudo", "-k"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        pass
