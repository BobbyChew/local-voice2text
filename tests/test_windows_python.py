"""Windows Store shim detection and safe interpreter re-spawn."""

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from local_voice2text.windows_python import (
    command_uses_bare_python,
    interpreter_command,
    is_windows_store_shim,
    spawn_python_module,
    warn_if_store_shim,
)

SHIM = r"C:\Users\me\AppData\Local\Microsoft\WindowsApps\python.exe"
SHIM_FWD = "C:/Users/me/AppData/Local/Microsoft/WindowsApps/python3.exe"
STORE_INSTALL = (
    r"C:\Users\me\AppData\Local\Microsoft\WindowsApps"
    r"\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\python.exe"
)
REAL = r"C:\Users\me\AppData\Local\Programs\Python\Python312\python.exe"


def test_detects_windowsapps_paths():
    assert is_windows_store_shim(SHIM)
    assert is_windows_store_shim(SHIM_FWD)
    assert is_windows_store_shim(STORE_INSTALL)
    assert is_windows_store_shim(SHIM.upper())
    assert not is_windows_store_shim(REAL)
    assert not is_windows_store_shim(r"C:\Python312\python.exe")
    assert not is_windows_store_shim("/usr/bin/python3")
    assert not is_windows_store_shim("")


def test_current_interpreter_is_not_a_shim_on_this_runner():
    # The CI / dev interpreter must not itself be the Store alias. Passing
    # None reads sys.executable.
    assert not is_windows_store_shim(None)
    assert "windowsapps" not in sys.executable.lower()


def test_warns_only_for_shim(capsys):
    assert warn_if_store_shim(SHIM) is True
    err = capsys.readouterr().err
    assert SHIM in err
    assert "WindowsApps" in err
    assert "py -3 -m local_voice2text" in err
    assert "second interpreter" in err
    assert "python.org" in err

    assert warn_if_store_shim(REAL) is False
    assert capsys.readouterr().err == ""


def test_interpreter_command_prefers_real_executable():
    assert interpreter_command(REAL) == [REAL]
    assert interpreter_command("/usr/bin/python3") == ["/usr/bin/python3"]
    assert not command_uses_bare_python(interpreter_command(REAL))


def test_interpreter_command_uses_py_launcher_for_shim():
    for path in (SHIM, SHIM_FWD, STORE_INSTALL):
        command = interpreter_command(path)
        assert command == ["py", "-3"], path
        assert not command_uses_bare_python(command)


def test_empty_executable_falls_back_without_store_alias(monkeypatch):
    monkeypatch.setattr(os, "name", "posix")
    assert interpreter_command("") == ["python3"]
    monkeypatch.setattr(os, "name", "nt")
    assert interpreter_command("") == ["py", "-3"]


def test_bare_python_on_windows_never_used(monkeypatch):
    monkeypatch.setattr(os, "name", "nt")
    for name in ("python", "python.exe", "python3", "python3.exe", r"Scripts\python.exe"):
        command = interpreter_command(name)
        assert command == ["py", "-3"]
        assert not command_uses_bare_python(command)
    assert interpreter_command(REAL) == [REAL]


def test_spawn_helper_does_not_use_bare_python_for_shim(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    spawn_python_module(
        "local_voice2text",
        ["audio.wav", "-o", "transcript.txt"],
        executable=SHIM,
        check=True,
    )
    assert captured["command"] == [
        "py",
        "-3",
        "-m",
        "local_voice2text",
        "audio.wav",
        "-o",
        "transcript.txt",
    ]
    assert captured["kwargs"]["check"] is True
    assert not command_uses_bare_python(captured["command"])


def test_package_sources_do_not_spawn_bare_python():
    root = Path(__file__).resolve().parents[1] / "local_voice2text"
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert '["python"' not in text
        assert "['python'" not in text
        assert '["python.exe"' not in text
        assert "['python.exe'" not in text


def test_spawn_helper_uses_sys_executable_when_real(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    spawn_python_module("local_voice2text", executable=REAL)
    assert captured["command"] == [REAL, "-m", "local_voice2text"]
