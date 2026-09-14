#!/bin/sh
#
# install.sh — Installer for the `os` command (oswrap).
#
# This script is POSIX sh compatible so that it can be safely piped
# into a shell:
#
#   curl -fsSL https://gitlab.com/jorgealbertojc/io.local.personal.helpers/-/raw/master/install.sh | sh
#
# What it does:
#   1. Verifies that curl and git are available.
#   2. Installs uv from the official installer if it is not already
#      present on PATH.
#   3. Installs the io-local-personal-helpers package as a uv tool,
#      pinning the requested release tag.
#   4. Activates argcomplete's global shell completion.
#   5. Prints a short summary with the command location and a usage
#      hint.
#
# Environment variables (all optional):
#   OSWRAP_VERSION   Git tag to install. Defaults to 1.0.1.
#   OSWRAP_REPO      Git repository URL. Defaults to the GitLab SSH
#                    URL. Change this to install from the GitHub
#                    mirror, a fork, or a local path.
#
# Requirements:
#   - SSH access to the GitLab repository (or wherever OSWRAP_REPO
#     points to). HTTPS URLs are also accepted by uv.
#   - git and curl available on PATH.

set -eu

OSWRAP_VERSION="${OSWRAP_VERSION:-1.0.1}"
OSWRAP_REPO="${OSWRAP_REPO:-git+ssh://git@gitlab.com/jorgealbertojc/io.local.personal.helpers.git}"

log() {
    printf '[oswrap] %s\n' "$*" >&2
}

die() {
    printf '[oswrap] ERROR: %s\n' "$*" >&2
    exit 1
}

# 1. Sanity checks ---------------------------------------------------------

command -v curl >/dev/null 2>&1 || die "curl is required but not installed."
command -v git  >/dev/null 2>&1 || die "git is required but not installed."

# 2. Ensure uv is available ------------------------------------------------

if ! command -v uv >/dev/null 2>&1; then
    log "uv not found. Installing from the official installer..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    PATH="$HOME/.local/bin:$PATH"
    export PATH
    command -v uv >/dev/null 2>&1 || die "uv installation failed."
fi

log "uv version: $(uv --version)"

# 3. Install the tool ------------------------------------------------------

log "Installing io-local-personal-helpers@${OSWRAP_VERSION}..."
uv tool install --force "${OSWRAP_REPO}@${OSWRAP_VERSION}"

# 4. Activate argcomplete global completion --------------------------------
#
# activate-global-python-argcomplete is idempotent: running it again
# simply rewrites the same hook file. Any command whose entry point
# carries the `# PYTHON_ARGCOMPLETE_OK` marker will then be completed
# by the shell without further per-command registration.

log "Activating argcomplete global shell completion..."
if ! uvx --from argcomplete activate-global-python-argcomplete --user; then
    log "WARNING: could not activate argcomplete."
    log "Shell completion will not work until you activate it manually:"
    log "  uvx --from argcomplete activate-global-python-argcomplete --user"
fi

# 5. Final message ---------------------------------------------------------

TOOL_BIN_DIR="$(uv tool dir --bin 2>/dev/null || printf '%s' "$HOME/.local/bin")"

printf '\n'
printf 'oswrap installed successfully.\n'
printf '\n'
printf '  Command:   os\n'
printf '  Version:   %s\n' "$OSWRAP_VERSION"
printf '  Location:  %s/os\n' "$TOOL_BIN_DIR"
printf '\n'
printf 'Verify it works:\n'
printf '\n'
printf '  os help\n'
printf '\n'
printf 'If shell completion does not work, restart your shell:\n'
printf '\n'
printf '  exec $SHELL\n'
printf '\n'
