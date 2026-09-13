"""Execution log file management for oswrap commands.

Every command wrapper writes its full stdout/stderr to a log file
under /tmp so that failures can be diagnosed after the fact without
cluttering the terminal. This module provides a thin, line-buffered
context manager around that file.
"""

import time
import uuid
from pathlib import Path
from types import TracebackType

_LOG_DIR = Path("/tmp")


class ExecutionLog:
    """Line-buffered execution log written to /tmp.

    File name format::

        <timestamp>-<uuid>-<name>.log

    where ``<timestamp>`` is the Unix epoch time with millisecond
    precision (e.g. ``1757625612.847``), ``<uuid>`` is a random UUID4
    to guarantee uniqueness across concurrent runs, and ``<name>`` is
    the caller-provided identifier for the command being logged.

    Intended to be used as a context manager::

        with ExecutionLog("apt-update") as log:
            log.write("Starting apt update...\\n")
            print(f"Log file: {log.path}")
    """

    def __init__(self, name: str) -> None:
        """Open a new log file under /tmp.

        Args:
            name: Short identifier for the command being logged, used
                as the trailing component of the file name (without
                the ``.log`` extension).

        Raises:
            OSError: If the log file cannot be created.
        """
        timestamp = f"{time.time():.3f}"
        execution_uuid = uuid.uuid4()
        self._path = _LOG_DIR / f"{timestamp}-{execution_uuid}-{name}.log"
        self._file = self._path.open("w", buffering=1, encoding="utf-8")

    @property
    def path(self) -> Path:
        """Absolute path of the log file on disk."""
        return self._path

    def write(self, line: str) -> None:
        """Write ``line`` to the log file.

        The underlying file is line-buffered, so any string ending in
        ``\\n`` is flushed to disk immediately. Strings without a
        trailing newline are held in the buffer until the next write
        or until :meth:`close` is called.
        """
        self._file.write(line)

    def close(self) -> None:
        """Close the underlying file. Idempotent."""
        if not self._file.closed:
            self._file.close()

    def __enter__(self) -> "ExecutionLog":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
