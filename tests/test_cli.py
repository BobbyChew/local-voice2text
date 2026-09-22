"""CLI startup warning and default pipeline flags."""

import sys
from pathlib import Path

from local_voice2text.cli import main
from local_voice2text.windows_python import is_windows_store_shim

SHIM = r"C:\Users\me\AppData\Local\Microsoft\WindowsApps\python.exe"


def _patch_transcribe(monkeypatch, sink):
    def fake(source, **kwargs):
        sink["source"] = source
        sink["kwargs"] = kwargs
        return "hello from whisper"

    monkeypatch.setattr("local_voice2text.cli.transcribe_file", fake)


def test_cli_warns_when_running_under_store_shim(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, "executable", SHIM)
    assert is_windows_store_shim()
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"RIFF")
    sink = {}
    _patch_transcribe(monkeypatch, sink)

    code = main([str(audio), "--model", "large-v3"])
    captured = capsys.readouterr()
    assert code == 0
    assert "hello from whisper" in captured.out
    assert "WindowsApps" in captured.err
    assert "py -3 -m local_voice2text" in captured.err
    assert sink["kwargs"]["model"] == "large-v3"
    assert sink["kwargs"]["vad_filter"] is False


def test_cli_silent_for_real_interpreter(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"RIFF")
    _patch_transcribe(monkeypatch, {})
    code = main([str(audio)])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""
    assert "hello from whisper" in captured.out


def test_cli_writes_output_file(monkeypatch, capsys, tmp_path):
    audio = tmp_path / "speech.mp4"
    audio.write_bytes(b"mp4")
    out = tmp_path / "transcript.txt"
    _patch_transcribe(monkeypatch, {})
    code = main([str(audio), "-o", str(out)])
    assert code == 0
    assert out.read_text(encoding="utf-8") == "hello from whisper\n"
    assert capsys.readouterr().out == ""


def test_cli_vad_flag(monkeypatch, tmp_path):
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"RIFF")
    sink = {}
    _patch_transcribe(monkeypatch, sink)
    assert main([str(audio), "--vad", "--language", "en"]) == 0
    assert sink["kwargs"]["vad_filter"] is True
    assert sink["kwargs"]["language"] == "en"


def test_cli_missing_input_is_an_error(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, "executable", SHIM)
    missing = tmp_path / "nope.wav"
    code = main([str(missing)])
    captured = capsys.readouterr()
    assert code == 1
    assert "input file not found" in captured.err
    # The shim warning still fires before the pipeline runs.
    assert "py -3 -m local_voice2text" in captured.err


def test_help_mentions_defaults(capsys):
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    help_text = capsys.readouterr().out
    assert "large-v3" in help_text
    assert "off by default" in help_text
