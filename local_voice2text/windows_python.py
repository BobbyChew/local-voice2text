"""Detect the Microsoft Store Python alias and choose a safe re-spawn command.

On Windows, ``python`` on PATH often resolves to the zero-byte app-execution
alias at ``%LOCALAPPDATA%\\Microsoft\\WindowsApps\\python.exe``. Launching a
long job through that alias — or re-spawning it with bare ``python`` while a
real CPython is also involved — can start two interpreters for one process
and stall the machine. Callers that start another Python must use
:func:`interpreter_command` (``sys.executable`` when it is a real install,
otherwise ``py -3``).
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Sequence

# Directory name of the Store app-execution aliases. Matched case-insensitively
# anywhere in the interpreter path, as requested for shim detection.
_WINDOWS_APPS_MARK = "windowsapps"

_BARE_PYTHON_NAMES = {
    "python",
    "python.exe",
    "python3",
    "python3.exe",
}


def is_windows_store_shim(executable: str | None = None) -> bool:
    """Return True when *executable* points at a Microsoft Store WindowsApps alias.

    ``None`` checks :data:`sys.executable`. Detection is a case-insensitive
    ``WindowsApps`` substring so both the ``python.exe`` stub and Store installs
    that live under that directory are covered.
    """
    path = sys.executable if executable is None else executable
    if not path:
        return False
    return _WINDOWS_APPS_MARK in str(path).lower()


def warn_if_store_shim(
    executable: str | None = None,
    *,
    stream=None,
) -> bool:
    """Write a stderr warning when the interpreter is a WindowsApps alias.

    Returns True when a warning was written. The process is not exited; a real
    Store CPython also lives under WindowsApps and can still run, but the user
    needs to see that this is the double-launch hazard.
    """
    path = sys.executable if executable is None else executable
    if not is_windows_store_shim(path):
        return False
    out = sys.stderr if stream is None else stream
    print(_warning_text(str(path)), file=out)
    return True


def _warning_text(executable: str) -> str:
    return (
        "warning: this Python is under the Microsoft Store WindowsApps directory "
        f"({executable}).\n"
        "The WindowsApps python.exe alias can launch a second interpreter "
        "for the same transcription job and stall on CPU.\n"
        "Use a real CPython instead. Preferred command:\n"
        "  py -3 -m local_voice2text ...\n"
        "A python.org or winget install, or the full path to its python.exe, "
        "also works.\n"
        "Do not rely on the WindowsApps shim alone.\n"
    )


def interpreter_command(executable: str | None = None) -> list[str]:
    """Argv prefix for starting Python again.

    Prefers the given executable (default :data:`sys.executable`) when it is a
    real install. When that path is the WindowsApps shim, or on Windows when
    the name is a bare ``python`` / ``python3`` that would be resolved through
    PATH, returns ``["py", "-3"]`` so the Python launcher selects a real
    CPython. Never returns bare ``python`` for a shim path.
    """
    path = sys.executable if executable is None else executable
    path = "" if path is None else str(path)
    # A WindowsApps path is never a safe re-spawn target, including when this
    # helper is evaluated off Windows (callers may pass a stored Windows path).
    if path and is_windows_store_shim(path):
        return ["py", "-3"]
    if not path or _unsafe_windows_name(path):
        return _launcher_or_python3()
    return [path]


def spawn_python_module(
    module: str,
    args: Sequence[str] | None = None,
    *,
    executable: str | None = None,
    **kwargs,
):
    """Run ``python -m module`` with :func:`interpreter_command`.

    This is the supported re-spawn helper. Do not call bare ``python`` on
    Windows when the Store shim is what PATH would resolve.
    """
    command = [*interpreter_command(executable), "-m", module, *(args or [])]
    return subprocess.run(command, **kwargs)


def _unsafe_windows_name(path: str) -> bool:
    """True for relative or bare interpreter names when running on Windows.

    ``python`` with no directory is how the Store alias gets launched. Absolute
    paths outside WindowsApps (including ``py.exe``) are left unchanged.
    Drive-letter paths are recognized even when this code is imported on POSIX
    during tests.
    """
    if os.name != "nt":
        return False
    if _is_windows_absolute(path):
        return False
    return True


def _is_windows_absolute(path: str) -> bool:
    if path.startswith("\\\\"):
        return True
    if len(path) >= 3 and path[0].isalpha() and path[1] == ":" and path[2] in "\\/":
        return True
    return os.path.isabs(path)


def _launcher_or_python3() -> list[str]:
    # ``py -3`` is the Windows launcher. Anywhere else, ``python3`` is the
    # explicit interpreter name and is not the WindowsApps alias.
    if os.name == "nt" or is_windows_store_shim(sys.executable):
        return ["py", "-3"]
    return ["python3"]


def command_uses_bare_python(command: Sequence[str]) -> bool:
    """Return True when *command* starts by asking PATH for ``python``."""
    if not command:
        return False
    return os.path.basename(command[0]).lower() in _BARE_PYTHON_NAMES
