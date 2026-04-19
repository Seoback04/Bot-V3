"""Capture PNG screenshots and optional DOM snapshots."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from app.browser.playwright_base import PlaywrightBase
from app.logger import get_logger


log = get_logger(__name__)


class Screenshotter:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def capture(
        self,
        browser: PlaywrightBase,
        *,
        dom_snapshot: bool = True,
        tag: str = "review",
    ) -> tuple[Optional[Path], Optional[Path]]:
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        png_path: Optional[Path] = self.output_dir / f"screenshot_{tag}_{ts}.png"
        try:
            browser.screenshot(png_path)
        except Exception as e:
            log.warning("Screenshot failed: %s", e)
            png_path = None

        html_path: Optional[Path] = None
        if dom_snapshot:
            try:
                html = browser.content()
                html_path = self.output_dir / f"dom_{tag}_{ts}.html"
                html_path.write_text(html, encoding="utf-8")
                log.info("Saved DOM snapshot: %s", html_path)
            except Exception as e:
                log.warning("DOM snapshot failed: %s", e)
                html_path = None

        return png_path, html_path
