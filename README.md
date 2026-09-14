# oswrap1

> A personal CLI wrapper for system administration commands on Ubuntu.

`oswrap` provides the `os` command: a single entry point for common
system administration tasks on Ubuntu 24.04 LTS. It wraps existing OS
tooling (starting with `apt`) and adds consistent behavior around
privileged operations, execution logging, and interactive prompts.

The project is designed to grow: adding a new wrapped command means
adding a module under `commands/` and registering it. Everything else
— dispatch, help, logging, sudo handling — is already in place.

---

## 📦 Requirements

- **Ubuntu 24.04 LTS** (or any Debian-based distribution with `apt`).
- **Python 3.12** or newer.
- **`uv`** as the dependency manager and tool runner.
- The current user must be **`root`** or a member of the **`sudo`**
  group to run privileged commands.

---

## 🚀 Installation

`oswrap` is not published on PyPI. It is installed directly from its
Git repository using `uv tool install`, which creates an isolated
environment for the tool and exposes the `os` executable in
`~/.local/bin` (or the directory reported by `uv tool dir --bin`).

### From a release tag (recommended)

```bash
uv tool install git+ssh://git@gitlab.com/jorgealbertojc/io.local.personal.helpers.git@1.0.0
```

### From the default branch (development)

```bash
uv tool install git+ssh://git@gitlab.com/jorgealbertojc/io.local.personal.helpers.git
```

### From a local clone

```bash
git clone git@gitlab.com:jorgealbertojc/io.local.personal.helpers.git
cd io.local.personal.helpers
uv tool install .
```

### Verify the installation

```bash
which os
os help
```

### Upgrade

```bash
uv tool install --force git+ssh://git@gitlab.com/jorgealbertojc/io.local.personal.helpers.git@<version>
```

### Uninstall

```bash
uv tool uninstall io-local-personal-helpers
```

This removes the executable and the isolated environment. It does not
touch any repository clone you may have.

---

## 🧭 Usage

```bash
os                     # print help and exit with code 2
os help                # print help and exit with code 0
os --help              # same as above
os -h                  # same as above
os <command> [options]
os <command> --help    # command-specific help
os <command> -h        # same as above
os <command> help      # same as above
```

### Universal flags

| Flag | Description |
|------|-------------|
| `help`, `--help`, `-h` | Show the general help message. |
| `-v`, `--verbose` | Mirror command output to the terminal while still writing it to the execution log. |

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success, or help was requested explicitly. |
| `1` | The command ran but failed. |
| `2` | Usage error: no arguments provided, or unknown command. |

---

## 🔧 Commands

### `os update`

Refresh the apt package index and upgrade installed packages.

```bash
os update [-v | --verbose]
os update [-h | --help]
os apt-update            # alias for "update"
```

**Workflow:**

1. Verify that the current user is `root` or a member of the `sudo`
   group.
2. Prompt for the sudo password once via `getpass`.
3. Run `apt update` non-interactively with
   `DEBIAN_FRONTEND=noninteractive`.
4. List the upgradable packages with `apt list --upgradable` and
   record them in the execution log.
5. Run `apt upgrade` with the same password, forcing
   `--force-confdef` and `--force-confold` for conffile handling and
   always including phased updates.
6. When apt reports that any package was upgraded, newly installed, or
   removed, refresh the Opera ffmpeg shared library symlink pointing
   at the snap-installed Chromium build.
7. Invalidate the sudo timestamp so the cached credential does not
   linger after the command finishes.

**Notes:**

- The sudo password is requested once and reused for both `apt update`
  and `apt upgrade`.
- All subprocess output is written to a log file under `/tmp`. On
  failure, the log is dumped to stderr.
- The command requires `sudo` to be installed and available in `PATH`.

---

## 📋 Execution logs

Every invocation of a command writes its full output to a log file
under `/tmp`, following this pattern:

```text
<timestamp>-<uuid>-<name>.log
```

Where:

- **`<timestamp>`** — Unix epoch time with millisecond precision
  (e.g. `1757625612.847`). Formatted via `time.time()` to avoid
  depending on non-portable `strftime` directives.
- **`<uuid>`** — Random UUID4, guaranteeing uniqueness across
  concurrent executions.
- **`<name>`** — Caller-provided identifier for the command being
  logged (e.g. `os-update`).

On failure, the log is dumped to stderr so the user can diagnose the
problem without leaving the terminal.

---

## 🏗️ Architecture

```
io.local.personal.helpers/
├── pyproject.toml
├── uv.lock
├── README.md
├── releases/
│   └── 1.0.0.md
└── src/
    └── oswrap/
        ├── __init__.py          # package metadata (__version__)
        ├── cli.py               # entry point: argument parsing and dispatch
        ├── helptext.py          # general help presentation
        ├── commands/
        │   ├── __init__.py      # command registry (CommandSpec, resolve, summaries)
        │   └── apt.py           # implementation of "os update"
        └── lib/
            ├── __init__.py
            ├── logs.py          # ExecutionLog context manager
            └── sudo.py          # sudo helpers
```

### Responsibilities

| Module | Responsibility |
|--------|----------------|
| `cli.py` | Parse `sys.argv`, dispatch to the command registry, invalidate sudo timestamp in a `finally` block. Nothing else. |
| `helptext.py` | Render the general help message. Receives the command summaries as an argument; has no compile-time dependency on `commands/`. |
| `commands/__init__.py` | Aggregates command modules into a registry. Exposes `resolve(name)` for dispatch by canonical name or alias, and `summaries()` for the general help. |
| `commands/apt.py` | Implementation of the `os update` workflow, including help text specific to the command. |
| `lib/logs.py` | `ExecutionLog` context manager for per-run log files under `/tmp`. |
| `lib/sudo.py` | Sudo membership checks, password prompting, streaming runner, and timestamp invalidation. |

### Adding a new command

1. Create `commands/<name>.py` exposing:
   - `run_<name>(verbose: bool = False) -> int`
   - `show_help() -> None`
2. Register it in `commands/__init__.py`:
   ```python
   COMMANDS: dict[str, CommandSpec] = {
       "update": CommandSpec(...),
       "<name>": CommandSpec(
           name="<name>",
           summary="One-line description for the general help.",
           run=<name>.run_<name>,
           help=<name>.show_help,
           aliases=(),
       ),
   }
   ```
3. That's it. `cli.py` and `helptext.py` do not need to change.

---

## 🧩 Design decisions

- **Package named `oswrap`, command named `os`.** The original
  implementation lived in a directory named `os`, which collided with
  the Python standard library module of the same name. The package is
  now `oswrap`; the `os` command name is preserved for users via the
  `[project.scripts]` entry point in `pyproject.toml`.

- **`src/` layout.** Prevents accidentally importing `oswrap` from the
  repository root without installing it, and matches the convention
  that `uv` and modern packaging tools assume by default.

- **Dynamic version from `__init__.py`.** The version is declared once
  in `src/oswrap/__init__.py` and read by hatchling via
  `[tool.hatch.version]`. This eliminates the classic
  double-source-of-truth problem between `pyproject.toml` and the
  package metadata.

- **Command registry with `CommandSpec`.** Each command module exposes
  a `run_*` callable and a `show_help` callable, plus metadata. `cli.py`
  performs dispatch through the registry instead of a chain of
  `if/elif`. Adding a new command means adding a module and one entry
  in `COMMANDS`.

- **`helptext.py` decoupled from the registry.** The general help
  function receives the command summaries as an argument rather than
  importing `commands` itself. This keeps the module free of
  compile-time dependencies and trivial to test.

- **`ExecutionLog` as a context manager.** Guarantees the log file is
  closed even when exceptions are raised inside a command. Exposes
  `.path` for reporting. Uses line-buffering and explicit UTF-8
  encoding to avoid locale surprises.

- **Sudo helpers namespaced in `lib/sudo.py`.** Public names without a
  leading underscore, since they are now module-scoped rather than
  file-private. `run_sudo_and_stream` feeds the password to stdin
  once, merges stdout/stderr, and streams to log, terminal, and/or an
  in-memory buffer. Exception handling is restricted to `OSError` so
  that `KeyboardInterrupt` and other `BaseException` subclasses
  propagate correctly.

- **Sudo timestamp invalidation.** After a command completes, `cli.py`
  runs `sudo -k` in a `finally` block. This forces the next sudo
  invocation to prompt for a password again, instead of leaving a
  cached credential valid for the default 15-minute window. The
  `finally` guarantees cleanup even when the command fails.

- **`--fix-missing` dropped from `apt update`.** The flag is intended
  for install/upgrade operations where a package might be missing from
  the repository; it has no effect on refreshing the package index.

- **Opera ffmpeg link isolated in a private helper.** The source path
  for the Chromium snap's `libffmpeg.so` cannot be discovered reliably
  at runtime, so it is hardcoded. A failure there is logged as a
  warning and does not abort the update, since the update itself
  already succeeded.

- **Exit code conventions.** `0` for success, `1` for a command that
  ran but failed, `2` for usage errors (no arguments, unknown command).
  Matches `argparse` and the majority of serious CLIs.

---

## 🛠️ Development

### Set up the environment

```bash
git clone git@gitlab.com:jorgealbertojc/io.local.personal.helpers.git
cd io.local.personal.helpers
uv sync
```

`uv sync` creates `.venv`, installs `oswrap` in editable mode, and
generates `uv.lock`. After that, you can run the CLI inside the
virtual environment:

```bash
uv run os help
uv run os update -v
```

### Run the CLI without installing the tool

```bash
uv run python -m oswrap.cli help
```

### Check the version

```bash
uv run python -c "import oswrap; print(oswrap.__version__)"
```

---

## 📝 Commit conventions

This repository follows
[Conventional Commits](https://www.conventionalcommits.org/):

- `feat(scope): ...` for new features.
- `fix(scope): ...` for bug fixes.
- `refactor(scope): ...` for code changes that neither fix a bug nor
  add a feature.
- `chore(scope): ...` for maintenance tasks.
- `docs(scope): ...` for documentation changes.

The commit body should explain **what** changed and **why**, not just
**how**. Design decisions belong in the body.

---

## 🏷️ Release process

1. Ensure `develop` is up to date.
2. Bump `__version__` in `src/oswrap/__init__.py`.
3. Add `releases/<version>.md` with the full release notes.
4. Commit both to `develop` and push.
5. Create the release branch: `git checkout -b v<version>`.
6. Merge into `master` with `--no-ff`.
7. Push `master` and the release branch.
8. Create the release with `glab release create <version>`.
9. Delete the release branch locally and remotely.
10. Push to the GitHub mirror.

Tag, release name, and release title never carry a `v` prefix. The
release branch does.

---

## ⚠️ Known limitations

- Only one command is available in this release: `os update`.
- The parsing of apt's summary line depends on the English output
  format. A future release will force `LC_ALL=C` for the apt
  subprocesses.
- No validation of unknown flags. `os update --frobnicate` silently
  ignores the unknown flag. A formal argument parser will be
  introduced alongside the second command.
- Ubuntu version is not validated at runtime; the help text mentions
  24.04 LTS purely as documentation.

---

## 🔗 Repository

- **Primary (GitLab):** https://gitlab.com/jorgealbertojc/io.local.personal.helpers
- **Mirror (GitHub):** https://github.com/jorgealbertojc/io.local.personal.helpers
