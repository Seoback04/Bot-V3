"""Browser automation layer (Playwright sync API)."""

from app.browser.playwright_base import PlaywrightBase
from app.browser.playwright_manager import browser_page

__all__ = ["PlaywrightBase", "browser_page"]
