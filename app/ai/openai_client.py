"""Thin, resilient wrapper around the OpenAI SDK."""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.logger import get_logger
from config.settings import SETTINGS


log = get_logger(__name__)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


class OpenAIClient:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or SETTINGS.openai_api_key
        self.model = model or SETTINGS.openai_model
        self._client = None

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            if not self.enabled:
                return None
            try:
                from openai import OpenAI
            except ImportError as e:
                log.error("openai SDK not installed: %s", e)
                return None
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def chat_json(self, system: str, user: str, *, temperature: float = 0.0) -> Optional[dict[str, Any]]:
        client = self._get_client()
        if client is None:
            log.info("OpenAI disabled; skipping AI call.")
            return None
        try:
            resp = client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
            )
            content = (resp.choices[0].message.content or "").strip()
        except Exception as e:
            log.warning("OpenAI call failed: %s", e)
            return None

        parsed = _safe_json_load(content)
        if parsed is None:
            log.warning("OpenAI returned unparseable JSON; content=%r", content[:400])
        return parsed


def _safe_json_load(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = _JSON_BLOCK_RE.search(text)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
