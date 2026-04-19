"""Lightweight text normalization helpers."""
from __future__ import annotations

import re
import unicodedata


_WS_RE = re.compile(r"\s+")


def normalize_whitespace(text: str) -> str:
    return _WS_RE.sub(" ", text or "").strip()


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "")


def clean(text: str) -> str:
    return normalize_whitespace(normalize_unicode(text))


def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    stripped = re.sub(r"[^0-9+]", "", phone)
    if stripped.count("+") > 1:
        stripped = "+" + stripped.replace("+", "")
    return stripped


def normalize_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if not re.match(r"^https?://", url, flags=re.IGNORECASE):
        return "https://" + url
    return url
