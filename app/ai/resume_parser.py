"""Resume -> CandidateProfile via AI, with deterministic fallback."""
from __future__ import annotations

import re
from typing import Optional

from pydantic import ValidationError

from app.ai.openai_client import OpenAIClient
from app.ai.prompts import RESUME_TO_PROFILE_SYSTEM, resume_to_profile_user
from app.logger import get_logger
from app.schemas import CandidateProfile
from app.utils.text_cleaner import clean, normalize_phone, normalize_url


log = get_logger(__name__)

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


class ResumeParser:
    def __init__(self, client: Optional[OpenAIClient] = None) -> None:
        self.client = client or OpenAIClient()

    def parse(self, resume_text: str) -> CandidateProfile:
        raw = resume_text or ""
        cleaned = clean(raw)
        if not cleaned:
            raise ValueError("Empty resume text.")

        payload = self.client.chat_json(
            RESUME_TO_PROFILE_SYSTEM,
            resume_to_profile_user(cleaned),
        )
        if payload is not None:
            try:
                return _post_process(CandidateProfile.model_validate(payload))
            except ValidationError as e:
                log.warning("AI resume output failed schema; falling back. err=%s", e)

        # Heuristic path needs per-line structure, so use the raw text.
        return _post_process(_heuristic_profile(raw))


def _post_process(profile: CandidateProfile) -> CandidateProfile:
    data = profile.model_dump()
    if data.get("phone"):
        data["phone"] = normalize_phone(data["phone"])
    for k in ("linkedin", "github", "portfolio"):
        if data.get(k):
            data[k] = normalize_url(data[k])
    return CandidateProfile.model_validate(data)


def _heuristic_profile(text: str) -> CandidateProfile:
    email = _first(EMAIL_RE.findall(text))
    phone = _first(PHONE_RE.findall(text))
    urls = URL_RE.findall(text)
    linkedin = _first([u for u in urls if "linkedin" in u.lower()])
    github = _first([u for u in urls if "github" in u.lower()])
    portfolio = _first([u for u in urls if u not in {linkedin, github}])

    name = "Unknown Candidate"
    skip_tokens = ("@", "http", "linkedin", "github", "portfolio", "summary",
                   "experience", "education", "skills", "projects",
                   "certifications", "phone", "email")
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        lower = s.lower()
        if any(tok in lower for tok in skip_tokens):
            continue
        if not (2 <= len(s.split()) <= 5):
            continue
        if all(c.isalpha() or c.isspace() or c in ".-'" for c in s):
            name = s
            break

    return CandidateProfile(
        full_name=name,
        email=email,
        phone=phone,
        linkedin=linkedin,
        github=github,
        portfolio=portfolio,
        summary=text[:400],
    )


def _first(xs):
    return xs[0] if xs else None
