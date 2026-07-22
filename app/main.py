"""Entry point for `python -m app.main`."""

from __future__ import annotations

from app.cli.commands import main


if __name__ == "__main__":
    raise SystemExit(main())
