"""Entry point. Delegates to the Typer CLI in app.cli."""
from __future__ import annotations

from app.cli import app


if __name__ == "__main__":
    app()
