"""Fill form fields, read back, and return per-field results."""
from __future__ import annotations

import os
import time
from typing import Any

from app.browser.playwright_base import PlaywrightBase
from app.logger import get_logger
from app.models import DEFAULT_RETRY
from app.schemas import DetectedField, FieldMapping, ValidationResult


log = get_logger(__name__)


class FormFiller:
    def __init__(self, browser: PlaywrightBase) -> None:
        self.browser = browser

    def fill_all(
        self,
        fields: list[DetectedField],
        mappings: list[FieldMapping],
    ) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        by_selector = {f.selector: f for f in fields}

        for m in mappings:
            field = by_selector.get(m.selector)
            if field is None:
                results.append(ValidationResult(
                    selector=m.selector, semantic=m.semantic, expected=m.value,
                    status="error", message="Field disappeared between scan and fill",
                ))
                continue
            if field.disabled:
                results.append(ValidationResult(
                    selector=m.selector, semantic=m.semantic, expected=m.value,
                    status="skipped", message="Field disabled",
                ))
                continue
            results.append(self._fill_one(field, m))
        return results

    def _fill_one(self, field: DetectedField, mapping: FieldMapping) -> ValidationResult:
        last_err: Exception | None = None
        for attempt in range(1, DEFAULT_RETRY.attempts + 1):
            try:
                self._dispatch(field, mapping.value)
                actual = self._read_back(field)
                if _equivalent(mapping.value, actual, field):
                    log.info(
                        "OK  %-22s selector=%s value=%r conf=%.2f",
                        field.semantic, field.selector, mapping.value, mapping.confidence,
                    )
                    return ValidationResult(
                        selector=field.selector, semantic=field.semantic,
                        expected=mapping.value, actual=actual, status="ok",
                    )
                log.warning(
                    "MISMATCH %-18s expected=%r actual=%r (attempt %d)",
                    field.semantic, mapping.value, actual, attempt,
                )
                last_err = RuntimeError(f"mismatch expected={mapping.value!r} actual={actual!r}")
            except Exception as e:
                last_err = e
                log.warning("Fill error on %s (attempt %d): %s", field.selector, attempt, e)
            delay = min(
                DEFAULT_RETRY.max_delay_seconds,
                DEFAULT_RETRY.base_delay_seconds * (2 ** (attempt - 1)),
            )
            time.sleep(delay)

        return ValidationResult(
            selector=field.selector, semantic=field.semantic, expected=mapping.value,
            status="mismatch" if isinstance(last_err, RuntimeError) else "error",
            message=str(last_err) if last_err else None,
        )

    def _dispatch(self, field: DetectedField, value: Any) -> None:
        kind = field.kind
        sel = field.selector
        b = self.browser

        if kind in {"text", "email", "tel", "url", "number", "textarea", "date"}:
            b.fill(sel, "" if value is None else str(value))
            return
        if kind == "select":
            b.select(sel, str(value))
            return
        if kind == "radio":
            self._check_radio(field, str(value))
            return
        if kind == "checkbox":
            b.check(sel, bool(value))
            return
        if kind == "file":
            b.upload(sel, str(value))
            return
        raise RuntimeError(f"Unsupported field kind: {kind}")

    def _check_radio(self, field: DetectedField, value: str) -> None:
        page = self.browser.page
        handle = page.locator(field.selector).first
        name = handle.get_attribute("name")
        if not name:
            raise RuntimeError(f"radio selector {field.selector} has no name attribute")
        radios = page.locator(f'input[type="radio"][name="{name}"]')
        target = value.strip().lower()
        count = radios.count()
        for i in range(count):
            r = radios.nth(i)
            rid = r.get_attribute("id")
            label_text = ""
            if rid:
                lab = page.locator(f'label[for="{rid}"]').first
                if lab.count():
                    label_text = (lab.inner_text() or "").strip().lower()
            val_attr = (r.get_attribute("value") or "").strip().lower()
            if target and (target == label_text or target == val_attr
                           or target in label_text or target in val_attr):
                r.check()
                return
        raise RuntimeError(f"No matching radio option for value={value!r}")

    def _read_back(self, field: DetectedField) -> Any:
        if field.kind == "radio":
            page = self.browser.page
            handle = page.locator(field.selector).first
            name = handle.get_attribute("name")
            if not name:
                return None
            radios = page.locator(f'input[type="radio"][name="{name}"]')
            for i in range(radios.count()):
                r = radios.nth(i)
                if r.is_checked():
                    rid = r.get_attribute("id")
                    if rid:
                        lab = page.locator(f'label[for="{rid}"]').first
                        if lab.count():
                            return (lab.inner_text() or "").strip()
                    return r.get_attribute("value")
            return None
        return self.browser.read_value(field.selector)


def _equivalent(expected: Any, actual: Any, field: DetectedField) -> bool:
    if field.kind == "checkbox":
        return bool(expected) == bool(actual)
    if field.kind == "file":
        if actual is None:
            return False
        return os.path.basename(str(expected)).lower() == str(actual).lower()
    if expected is None and (actual is None or actual == ""):
        return True
    if actual is None:
        return False
    return str(expected).strip().lower() == str(actual).strip().lower()
