"""Allow ``py -3 -m local_voice2text``."""

from local_voice2text.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
