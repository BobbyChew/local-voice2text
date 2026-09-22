# local-voice2text

Local speech-to-text command line. The tool converts an audio or video file to 16 kHz mono WAV with ffmpeg, then transcribes that WAV with [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

The default model is `large-v3`. Voice-activity detection is **off** unless you pass `--vad`.

License: MIT.

## Requirements

- Python 3.9 or newer (a real CPython; see Windows below)
- [ffmpeg](https://ffmpeg.org/) on `PATH`
- Enough disk and RAM for the Whisper model (the first run downloads it)

## Windows

`python` on a typical Windows `PATH` is **not** CPython. It is the Microsoft Store app-execution alias:

`%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe`

(and the matching `python3.exe`). That file is a stub. Starting a long transcription through it, or mixing the stub with a real CPython install, can launch **two interpreter processes for one job**. Both load the model, the CPU pegs, and the run stalls.

Do not rely on the WindowsApps shim alone.

Use one of these instead:

1. **Python launcher (preferred).** The `py` launcher picks an installed CPython and does not go through the Store alias:

   ```bat
   py -3 -m pip install -r requirements.txt
   py -3 -m local_voice2text path\to\audio.wav
   py -3 -m local_voice2text path\to\video.mp4 -o transcript.txt
   ```

2. **A real CPython** from [python.org](https://www.python.org/downloads/windows/) or winget:

   ```bat
   winget install Python.Python.3.12
   ```

   Call that install by full path, for example:

   ```bat
   "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m local_voice2text path\to\audio.wav
   ```

3. **Turn the aliases off** so a bare `python` cannot hit the stub: Settings → Apps → Advanced app settings → App execution aliases → off for `python.exe` and `python3.exe`. After that, open a new terminal and confirm `where python` is **not** under `WindowsApps`.

Install ffmpeg the same way if it is missing:

```bat
winget install Gyan.FFmpeg
```

If you start the CLI under the shim anyway, it prints a warning on stderr and tells you to re-run with `py -3 -m local_voice2text`. Any helper in this package that starts another Python uses `sys.executable` when that path is a real install, and `py -3` when the path contains `WindowsApps`. It does not call bare `python` in that case.

## Other platforms

```bash
python3 -m pip install -r requirements.txt
python3 -m local_voice2text audio.wav
```

Editable install from a clone:

```bash
python3 -m pip install -e .
```

On Windows, use `py -3 -m pip` as shown above instead of `python3`.

## Usage

```bash
py -3 -m local_voice2text audio.wav
py -3 -m local_voice2text video.mp4 -o transcript.txt
py -3 -m local_voice2text audio.wav --model large-v3 --language en
py -3 -m local_voice2text audio.wav --vad
```

The `local-voice2text` console script is the same entry point when the install's scripts directory is on `PATH`. Prefer `py -3 -m local_voice2text` on Windows so you are not depending on whichever `python` the script shebang finds.

| Option | Default | Meaning |
| --- | --- | --- |
| `--model` | `large-v3` | faster-whisper model name or path |
| `--vad` | off | Enable voice-activity detection |
| `--language` | auto | Language code such as `en` |
| `--device` | `auto` | Passed through to faster-whisper |
| `--compute-type` | `default` | Passed through to faster-whisper |
| `-o`, `--output` | stdout | Transcript file (UTF-8) |

Transcripts are plain text, one non-empty Whisper segment per line.

## Pipeline

1. **ffmpeg** reads the input and writes a temporary 16 kHz, mono, 16-bit PCM WAV (`-ac 1 -ar 16000 -c:a pcm_s16le`). Video tracks are dropped.
2. **faster-whisper** transcribes that WAV. The model default is `large-v3`. `vad_filter` is false unless `--vad` is set. Inference uses a single worker so the job does not fork extra Python processes.
3. The temporary WAV is deleted when the process exits the transcription call.

## Development

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest
```

## License

MIT. See [LICENSE](LICENSE).
