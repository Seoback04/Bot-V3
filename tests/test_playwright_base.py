"""Hermetic tests for PlaywrightBase lifecycle and retries."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.browser.playwright_base import PlaywrightBase
from app.exceptions import BrowserError
from app.models import RetryPolicy


class _FakePW:
    def __init__(self) -> None:
        self.chromium = MagicMock()
        self.stopped = False
        page = MagicMock()
        page.evaluate.return_value = "hello"
        context = MagicMock()
        context.new_page.return_value = page
        browser = MagicMock()
        browser.new_context.return_value = context
        self.chromium.launch.return_value = browser
        self._page = page
        self._context = context
        self._browser = browser

    def stop(self) -> None:
        self.stopped = True


class _Base(PlaywrightBase):
    def __init__(self, pw: _FakePW, **kw) -> None:
        super().__init__(**kw)
        self._fake_pw = pw

    def _create_playwright(self):
        return self._fake_pw


def test_context_manager_starts_and_stops():
    fake = _FakePW()
    with _Base(fake, headless=True) as b:
        assert b.page is fake._page
    fake._context.close.assert_called_once()
    fake._browser.close.assert_called_once()
    assert fake.stopped is True


def test_page_access_before_start_raises():
    with pytest.raises(BrowserError):
        _ = _Base(_FakePW()).page


def test_goto_invokes_page_goto():
    fake = _FakePW()
    with _Base(fake) as b:
        b.goto("http://example.com")
    args, kwargs = fake._page.goto.call_args
    assert args[0] == "http://example.com"
    assert kwargs.get("wait_until") == "domcontentloaded"


def test_retry_then_success():
    fake = _FakePW()
    fake._page.goto.side_effect = [RuntimeError("boom"), None]
    with _Base(fake, retry_policy=RetryPolicy(attempts=3, base_delay_seconds=0.0, max_delay_seconds=0.0)) as b:
        b.goto("http://example.com")
    assert fake._page.goto.call_count == 2


def test_retry_exhaustion_raises_browser_error():
    fake = _FakePW()
    fake._page.goto.side_effect = RuntimeError("persistent")
    with _Base(fake, retry_policy=RetryPolicy(attempts=2, base_delay_seconds=0.0, max_delay_seconds=0.0)) as b:
        with pytest.raises(BrowserError):
            b.goto("http://example.com")
    assert fake._page.goto.call_count == 2


def test_read_value_uses_locator_evaluate():
    fake = _FakePW()
    loc = MagicMock()
    loc.first = loc
    loc.evaluate.return_value = "jane@example.com"
    fake._page.locator.return_value = loc
    with _Base(fake) as b:
        assert b.read_value("#email") == "jane@example.com"
    loc.evaluate.assert_called_once()
