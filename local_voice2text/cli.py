"""Command-line entry for local speech-to-text."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from local_voice2text import __version__
from local_voice2text.pipeline import (
    DEFAULT_COMPUTE_TYPE,
    DEFAULT_DEVICE,
    DEFAULT_MODEL,
    transcribe_file,
)
from local_voice2text.windows_python import warn_if_store_shim


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="local-voice2text",
        description=(
            "Transcribe audio or video locally. ffmpeg converts the input to "
            "16 kHz mono WAV, then faster-whisper transcribes it. "
            "Voice-activity detection is off unless --vad is set."
        ),
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Audio or video file to transcribe",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write the transcript to this file (default: stdout)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"faster-whisper model name (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--vad",
        action="store_true",
        help="Enable voice-activity detection (off by default)",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Language code such as en. Omit to auto-detect",
    )
    parser.add_argument(
        "--device",
        default=DEFAULT_DEVICE,
        help=f"faster-whisper device (default: {DEFAULT_DEVICE})",
    )
    parser.add_argument(
        "--compute-type",
        default=DEFAULT_COMPUTE_TYPE,
        help=f"faster-whisper compute type (default: {DEFAULT_COMPUTE_TYPE})",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Warns on stderr when Python is the WindowsApps shim."""
    warn_if_store_shim()
    args = build_parser().parse_args(argv)
    try:
        text = transcribe_file(
            args.input,
            model=args.model,
            vad_filter=args.vad,
            language=args.language,
            device=args.device,
            compute_type=args.compute_type,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error: transcription failed: {exc}", file=sys.stderr)
        return 1

    payload = text.strip() + "\n"
    if args.output is None:
        sys.stdout.write(payload)
    else:
        args.output.write_text(payload, encoding="utf-8")
    return 0


def cli_main() -> None:
    """Console-script entry point. Propagates the status code."""
    raise SystemExit(main())
