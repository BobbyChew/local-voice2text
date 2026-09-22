"""The Windows install notes are part of the public contract."""

from pathlib import Path

README = Path(__file__).resolve().parents[1].joinpath("README.md").read_text(encoding="utf-8")


def test_readme_warns_about_windowsapps_shim():
    assert "WindowsApps" in README
    assert "py -3 -m local_voice2text" in README
    assert "python.org" in README
    assert "winget" in README
    assert "Do not rely on the WindowsApps shim alone." in README


def test_readme_documents_pipeline_defaults():
    lowered = README.lower()
    assert "large-v3" in lowered
    assert "16 khz" in lowered
    assert "mono" in lowered
    assert "faster-whisper" in lowered
    assert "--vad" in lowered
    assert "mit" in lowered
