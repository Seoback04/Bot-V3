"""Context-manager factory yielding a started PlaywrightBase."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from app.browser.playwright_base import PlaywrightBase


@contextmanager
def browser_page(headless: Optional[bool] = None) -> Iterator[PlaywrightBase]:
    b = PlaywrightBase(headless=headless)
    b.start()
    try:
        yield b
    finally:
        b.stop()
