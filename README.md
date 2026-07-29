# io.local.personal.helpers

This repository contains personal local helper utilities. It currently includes Ubuntu-specific shell tooling that automates package maintenance and browser library configuration.

## Included tools

### `shell/ubuntu/io.local.personal.helpers.update-ubuntu`

A Bash script for Ubuntu systems.

Capabilities:

- Updates the APT package index.
- Performs a full package upgrade with `apt upgrade`.
- Creates or updates a symbolic link for `libffmpeg.so` used by Opera, sourcing the library from Chromium installed via Snap.
- Writes command output and error details to a temporary log file in `/tmp`.

Requirements:

- Must be executed as `root` or with `sudo`.

Usage:

```bash
sudo ./shell/ubuntu/io.local.personal.helpers.update-ubuntu
```

## Repository structure

- `shell/ubuntu/`
  - `io.local.personal.helpers.update-ubuntu`: Ubuntu maintenance and package configuration script.

## Contribution guidelines

This repository is intended to centralize personal helper scripts. To add a new utility, create a new script in the appropriate directory and document its usage in this README.
