# io.local.personal.helpers

This repository contains personal system helper utilities for Ubuntu environments. The current implementation provides a Python-based command named `os` that acts as a lightweight system administration entrypoint.

## Overview

The command is located in the `binaries/` directory and is exposed through a symlink so it can be invoked directly from the shell as `os`.

### Current command modules

- `binaries/os.py`: executable command entrypoint.
- `binaries/help.py`: help and usage text for the command.
- `binaries/apt.py`: implementation of the update workflow for Ubuntu package management.

The command currently supports:

- `os` - prints a basic initialization message.
- `os --help` or `os help` - shows usage information.
- `os update` - runs the update and upgrade workflow for the system.
- `os update -v` or `os update --verbose` - runs the same update workflow but also
    prints full output from `apt` commands to the terminal while still writing
    all output to the execution log.

## Requirements

The current implementation depends on the following:

- Python 3
- `sudo`
- membership in the `sudo` group for the update workflow
- `apt` on Ubuntu 24.04 LTS
- a writable `~/.local/bin` directory if you want to install the command in the user-local PATH

## Installation

To install the command globally for your user session, clone the repository and create a symlink from the project `os.py` entrypoint into a directory that is already present in your `PATH`.

Example:

```bash
ln -svf \
    ${HOME}/Development/gitlab.com/jorgealbertojc/io.local.personal.helpers/binaries/os.py \
    ${HOME}/.local/bin/os
```

If `~/.local/bin` is not already in your `PATH`, make sure it is exported in your shell profile, for example:

```bash
export PATH="${HOME}/.local/bin:${PATH}"
```

After that, the command can be invoked as:

```bash
os --help
```

## Usage

### Help

```bash
os --help
os help
```

This prints a small man-page style description of the command, usage, and supported options.

### Update workflow

```bash
os update
os update -v
```

The current `update` workflow performs the following actions:

1. Validates that the current user belongs to the `sudo` group.
2. Prompts for the sudo password once and reuses it for the entire operation.
3. Runs `apt update` with non-interactive flags.
4. Lists packages that are available for upgrade (package names only).
5. Executes `apt upgrade` using the same sudo session context. By default the
    command writes the detailed command output to the execution log and prints
    minimal informational messages to the terminal. Use `-v|--verbose` to mirror
    full command output to the terminal as well as the log file.
6. If the upgrade installed packages and the Opera ffmpeg library needs to be
    repaired, the command creates or updates a symlink for Opera's `libffmpeg.so`
    pointing to the Chromium snap-provided library.
7. Writes all command output to a temporary log file in `/tmp` with a UUID and
    timestamp in the filename.

## Log behavior

The `os update` workflow is designed to keep command output off the terminal unless an execution error occurs.

Logs are stored in `/tmp` using the following naming pattern:

```bash
/tmp/<timestamp>-<uuid>-os-update.log
```

If an error occurs, the user is informed and the log path is reported so the execution can be inspected.

## Repository layout

- `binaries/` — executable Python command modules (current entrypoint is `os`).

Note: legacy shell helpers are not included in this repository; the Python `os` command
replaces the older shell-only updater workflow.

## Notes

This command is still evolving. The current scope is focused on Ubuntu package maintenance and general system administration convenience workflows.
