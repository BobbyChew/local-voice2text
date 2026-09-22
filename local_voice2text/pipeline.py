"""ffmpeg to 16 kHz mono WAV, then faster-whisper.

Voice-activity detection is off unless the caller passes ``vad_filter=True``.
The default model is ``large-v3``. ``WhisperModel`` is constructed with
``num_workers=1`` so transcription stays in this process instead of spawning
extra interpreters (those children would re-launch ``sys.executable``).
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

DEFAULT_MODEL = "large-v3"
DEFAULT_VAD = False
DEFAULT_DEVICE = "auto"
DEFAULT_COMPUTE_TYPE = "default"
SAMPLE_RATE = 16000
# One worker keeps model inference in-process. Extra workers are child
# processes and are how a Store-shim ``sys.executable`` gets launched twice.
NUM_WORKERS = 1


def ffmpeg_command(source: Path, wav_path: Path) -> list[str]:
    """Build the ffmpeg argv that extracts 16 kHz mono 16-bit PCM WAV."""
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        "-c:a",
        "pcm_s16le",
        str(wav_path),
    ]


def extract_wav(source: Path, wav_path: Path) -> None:
    """Convert *source* to a 16 kHz mono WAV at *wav_path* using ffmpeg."""
    source = Path(source)
    wav_path = Path(wav_path)
    if not source.is_file():
        raise FileNotFoundError(f"input file not found: {source}")
    try:
        subprocess.run(
            ffmpeg_command(source, wav_path),
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            "ffmpeg was not found on PATH. Install ffmpeg and try again."
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        message = "ffmpeg failed to extract audio"
        if detail:
            message = f"{message}: {detail}"
        raise RuntimeError(message) from exc


def transcribe_wav(
    wav_path: Path,
    *,
    model: str = DEFAULT_MODEL,
    vad_filter: bool = DEFAULT_VAD,
    language: str | None = None,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
) -> str:
    """Transcribe a WAV file with faster-whisper. VAD is off by default."""
    from faster_whisper import WhisperModel

    whisper = WhisperModel(
        model,
        device=device,
        compute_type=compute_type,
        num_workers=NUM_WORKERS,
    )
    segments, _info = whisper.transcribe(
        str(wav_path),
        vad_filter=vad_filter,
        language=language,
    )
    lines = []
    for segment in segments:
        text = (segment.text or "").strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def transcribe_file(
    source: Path,
    *,
    model: str = DEFAULT_MODEL,
    vad_filter: bool = DEFAULT_VAD,
    language: str | None = None,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
) -> str:
    """Extract 16 kHz mono WAV with ffmpeg, then transcribe it."""
    source = Path(source)
    with tempfile.TemporaryDirectory(prefix="local-voice2text-") as tmp:
        wav_path = Path(tmp) / "audio.wav"
        extract_wav(source, wav_path)
        return transcribe_wav(
            wav_path,
            model=model,
            vad_filter=vad_filter,
            language=language,
            device=device,
            compute_type=compute_type,
        )
