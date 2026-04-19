"""Playwright automation base class: lifecycle, retries, resilient utilities."""
from __future__ import annotations

import time
from pathlib import Path
from types import TracebackType
from typing import Any, Callable, Optional, Type

from app.exceptions import BrowserError
from app.logger import get_logger
from app.models import DEFAULT_RETRY, RetryPolicy
from config.settings import SETTINGS


log = get_logger(__name__)


class PlaywrightBase:
    """Lifecycle + utility layer over Playwright's sync API."""

    def __init__(
        self,
        *,
        headless: Optional[bool] = None,
        default_timeout_ms: int = 10_000,
        retry_policy: RetryPolicy = DEFAULT_RETRY,
        user_agent: Optional[str] = None,
    ) -> None:
        self._headless = SETTINGS.headless if headless is None else bool(headless)
        self._default_timeout_ms = default_timeout_ms
        self._retry = retry_policy
        self._user_agent = user_agent

        self._pw = None
        self._browser = None
        self._context = None
        self._page = None

    def start(self) -> "PlaywrightBase":
        if self._page is not None:
            return self
        pw = self._create_playwright()
        log.info("Launching Chromium (headless=%s)", self._headless)
        try:
            browser = pw.chromium.launch(headless=self._headless)
            ctx_kwargs: dict[str, Any] = {}
            if self._user_agent:
                ctx_kwargs["user_agent"] = self._user_agent
            context = browser.new_context(**ctx_kwargs)
            context.set_default_timeout(self._default_timeout_ms)
            page = context.new_page()
        except Exception as e:
            try:
                pw.stop()
            except Exception:
                pass
            raise BrowserError(f"Failed to launch browser: {e}") from e

        self._pw, self._browser, self._context, self._page = pw, browser, context, page
        return self

    def stop(self) -> None:
        for name, obj in (("context", self._context), ("browser", self._browser), ("playwright", self._pw)):
            if obj is None:
                continue
            try:
                obj.stop() if name == "playwright" else obj.close()
            except Exception as e:
                log.warning("Error closing %s: %s", name, e)
        self._pw = self._browser = self._context = self._page = None

    def __enter__(self) -> "PlaywrightBase":
        return self.start()

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.stop()

    @property
    def page(self):
        if self._page is None:
            raise BrowserError("Browser not started. Call .start() or use as context manager.")
        return self._page

    @property
    def context(self):
        if self._context is None:
            raise BrowserError("Browser not started.")
        return self._context

    def goto(self, url: str, *, wait_until: str = "domcontentloaded") -> None:
        log.info("Navigating to %s", url)
        self._with_retry(lambda: self.page.goto(url, wait_until=wait_until), op=f"goto({url!r})")

    def locator(self, selector: str):
        return self.page.locator(selector).first

    def fill(self, selector: str, value: str) -> None:
        def _do() -> None:
            loc = self.locator(selector)
            loc.wait_for(state="visible", timeout=self._default_timeout_ms)
            loc.fill("")
            loc.fill("" if value is None else str(value))
        self._with_retry(_do, op=f"fill({selector!r})")

    def select(self, selector: str, value_or_label: str) -> None:
        def _do() -> None:
            loc = self.locator(selector)
            loc.wait_for(state="visible", timeout=self._default_timeout_ms)
            try:
                loc.select_option(label=str(value_or_label))
            except Exception:
                loc.select_option(value=str(value_or_label))
        self._with_retry(_do, op=f"select({selector!r})")

    def check(self, selector: str, checked: bool = True) -> None:
        def _do() -> None:
            loc = self.locator(selector)
            loc.wait_for(state="visible", timeout=self._default_timeout_ms)
            loc.check() if checked else loc.uncheck()
        self._with_retry(_do, op=f"check({selector!r},{checked})")

    def upload(self, selector: str, file_path: str | Path) -> None:
        path_str = str(file_path)
        self._with_retry(lambda: self.locator(selector).set_input_files(path_str), op=f"upload({selector!r})")

    def read_value(self, selector: str) -> Any:
        script = """el => {
            if (!el) return null;
            const tag = el.tagName.toLowerCase();
            if (tag === 'select') {
                return el.options[el.selectedIndex] ? el.options[el.selectedIndex].text : null;
            }
            if (el.type === 'checkbox') return !!el.checked;
            if (el.type === 'radio') return el.checked ? (el.value || true) : false;
            if (el.type === 'file') return (el.files && el.files[0]) ? el.files[0].name : null;
            return el.value ?? null;
        }"""
        return self._with_retry(lambda: self.locator(selector).evaluate(script), op=f"read_value({selector!r})")

    def evaluate(self, script: str, *args: Any) -> Any:
        return self.page.evaluate(script, *args)

    def screenshot(self, path: str | Path, *, full_page: bool = True) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(p), full_page=full_page)
        log.info("Saved screenshot: %s", p)
        return p

    def content(self) -> str:
        return self.page.content()

    def _create_playwright(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise BrowserError("playwright is not installed") from e
        return sync_playwright().start()

    def _with_retry(self, fn: Callable[[], Any], *, op: str) -> Any:
        last_err: Optional[Exception] = None
        for attempt in range(1, self._retry.attempts + 1):
            try:
                return fn()
            except Exception as e:
                last_err = e
                delay = min(
                    self._retry.max_delay_seconds,
                    self._retry.base_delay_seconds * (2 ** (attempt - 1)),
                )
                log.warning(
                    "Op %s failed on attempt %d/%d: %s (retry in %.2fs)",
                    op, attempt, self._retry.attempts, e, delay,
                )
                time.sleep(delay)
        raise BrowserError(f"{op} failed after {self._retry.attempts} attempts: {last_err}") from last_err
