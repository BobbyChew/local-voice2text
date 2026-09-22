"""Pipeline defaults: 16 kHz mono WAV, large-v3, VAD off."""

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from local_voice2text.pipeline import (
    DEFAULT_MODEL,
    DEFAULT_VAD,
    NUM_WORKERS,
    SAMPLE_RATE,
    extract_wav,
    ffmpeg_command,
    transcribe_file,
    transcribe_wav,
)


def test_ffmpeg_command_is_16k_mono_wav():
    cmd = ffmpeg_command(Path("speech.mp4"), Path("audio.wav"))
    assert cmd[0] == "ffmpeg"
    assert cmd[cmd.index("-ac") + 1] == "1"
    assert cmd[cmd.index("-ar") + 1] == str(SAMPLE_RATE)
    assert SAMPLE_RATE == 16000
    assert cmd[cmd.index("-c:a") + 1] == "pcm_s16le"
    assert "-vn" in cmd
    assert "speech.mp4" in cmd
    assert "audio.wav" in cmd


def test_extract_wav_requires_input(tmp_path):
    with pytest.raises(FileNotFoundError, match="input file not found"):
        extract_wav(tmp_path / "missing.wav", tmp_path / "out.wav")


def test_extract_wav_reports_missing_ffmpeg(monkeypatch, tmp_path):
    source = tmp_path / "audio.wav"
    source.write_bytes(b"not really wav")

    def boom(*_args, **_kwargs):
        raise FileNotFoundError(2, "No such file")

    monkeypatch.setattr(subprocess, "run", boom)
    with pytest.raises(FileNotFoundError, match="ffmpeg was not found"):
        extract_wav(source, tmp_path / "out.wav")


def test_extract_wav_reports_ffmpeg_failure(monkeypatch, tmp_path):
    source = tmp_path / "audio.wav"
    source.write_bytes(b"data")

    def fail(*_args, **_kwargs):
        raise subprocess.CalledProcessError(1, "ffmpeg", stderr="invalid data")

    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(RuntimeError, match="invalid data"):
        extract_wav(source, tmp_path / "out.wav")


def test_transcribe_wav_defaults(monkeypatch, tmp_path):
    calls = {}

    class FakeModel:
        def __init__(self, model_size, device, compute_type, num_workers):
            calls["init"] = {
                "model": model_size,
                "device": device,
                "compute_type": compute_type,
                "num_workers": num_workers,
            }

        def transcribe(self, path, vad_filter, language):
            calls["transcribe"] = {
                "path": path,
                "vad_filter": vad_filter,
                "language": language,
            }
            segments = [
                SimpleNamespace(text=" hello "),
                SimpleNamespace(text="   "),
                SimpleNamespace(text="world"),
            ]
            return segments, SimpleNamespace(language="en")

    monkeypatch.setitem(
        sys.modules,
        "faster_whisper",
        SimpleNamespace(WhisperModel=FakeModel),
    )
    wav_path = tmp_path / "audio.wav"
    wav_path.write_bytes(b"RIFF")
    text = transcribe_wav(wav_path)
    assert text == "hello\nworld"
    assert calls["init"]["model"] == DEFAULT_MODEL == "large-v3"
    assert calls["init"]["num_workers"] == NUM_WORKERS == 1
    assert calls["transcribe"]["vad_filter"] is DEFAULT_VAD is False
    assert calls["transcribe"]["language"] is None


def test_transcribe_file_runs_ffmpeg_then_whisper(monkeypatch, tmp_path):
    order = []
    source = tmp_path / "video.mp4"
    source.write_bytes(b"video")

    def fake_extract(src, wav_path):
        order.append("ffmpeg")
        assert src == source
        wav_path.write_bytes(b"wav")

    def fake_transcribe(wav_path, **kwargs):
        order.append("whisper")
        assert wav_path.is_file()
        assert kwargs["model"] == "large-v3"
        assert kwargs["vad_filter"] is False
        return "transcript"

    monkeypatch.setattr("local_voice2text.pipeline.extract_wav", fake_extract)
    monkeypatch.setattr("local_voice2text.pipeline.transcribe_wav", fake_transcribe)
    assert transcribe_file(source) == "transcript"
    assert order == ["ffmpeg", "whisper"]
