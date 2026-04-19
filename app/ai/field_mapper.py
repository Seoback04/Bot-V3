"""Map CandidateProfile onto DetectedFields."""
from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import ValidationError

from app.ai.openai_client import OpenAIClient
from app.ai.prompts import FIELD_MAPPING_SYSTEM, field_mapping_user
from app.logger import get_logger
from app.models import HIGH_CONFIDENCE_THRESHOLD
from app.schemas import CandidateProfile, DetectedField, FieldMapping


log = get_logger(__name__)


_DETERMINISTIC: dict[str, Any] = {
    "full_name": lambda p: p.full_name,
    "first_name": lambda p: (p.full_name or "").split()[0] if p.full_name else None,
    "last_name": lambda p: " ".join((p.full_name or "").split()[1:]) or None,
    "email": lambda p: p.email,
    "phone": lambda p: p.phone,
    "linkedin": lambda p: p.linkedin,
    "github": lambda p: p.github,
    "portfolio": lambda p: p.portfolio,
    "website": lambda p: p.portfolio,
    "city": lambda p: _city_from_location(p.location),
    "country": lambda p: _country_from_location(p.location),
    "address": lambda p: p.location,
    "summary": lambda p: p.summary,
    "cover_letter": lambda p: p.summary,
    "years_of_experience": lambda p: p.years_of_experience,
    "work_authorization": lambda p: p.work_authorization,
    "preferred_job_title": lambda p: (p.preferred_job_titles or [None])[0],
    "skills": lambda p: ", ".join(p.skills) if p.skills else None,
    "certifications": lambda p: ", ".join(p.certifications) if p.certifications else None,
    "education_degree": lambda p: (p.education[0].degree if p.education else None),
    "education_institution": lambda p: (p.education[0].institution if p.education else None),
    "current_title": lambda p: (p.work_experience[0].title if p.work_experience else None),
    "current_company": lambda p: (p.work_experience[0].company if p.work_experience else None),
}


def _city_from_location(loc: Optional[str]) -> Optional[str]:
    if not loc:
        return None
    return loc.split(",")[0].strip() or None


def _country_from_location(loc: Optional[str]) -> Optional[str]:
    if not loc:
        return None
    parts = [p.strip() for p in loc.split(",") if p.strip()]
    return parts[-1] if len(parts) >= 2 else None


class FieldMapper:
    def __init__(
        self,
        client: Optional[OpenAIClient] = None,
        resume_file_path: Optional[str] = None,
    ) -> None:
        self.client = client or OpenAIClient()
        self.resume_file_path = resume_file_path

    def map(self, profile: CandidateProfile, fields: list[DetectedField]) -> list[FieldMapping]:
        mappings: dict[str, FieldMapping] = {}

        for f in fields:
            if f.disabled:
                continue
            value = self._deterministic_value(profile, f)
            if value is None or value == "":
                continue
            value = self._coerce_for_field(value, f)
            if value is None:
                continue
            mappings[f.selector] = FieldMapping(
                selector=f.selector,
                semantic=f.semantic,
                value=value,
                confidence=HIGH_CONFIDENCE_THRESHOLD,
                reason="deterministic",
            )

        remaining = [f for f in fields if f.selector not in mappings and not f.disabled]
        if remaining:
            for m in self._ai_map(profile, remaining):
                mappings.setdefault(m.selector, m)

        return list(mappings.values())

    def _deterministic_value(self, profile: CandidateProfile, field: DetectedField) -> Any:
        sem = field.semantic
        if sem == "resume_upload" and self.resume_file_path:
            return self.resume_file_path
        if sem == "consent" and field.kind == "checkbox":
            return True
        if sem == "visa_sponsorship" and field.kind in {"radio", "select", "checkbox"}:
            if profile.work_authorization and "citizen" in profile.work_authorization.lower():
                return _pick_yes_no(field, want_yes=False)
            return None
        fn = _DETERMINISTIC.get(sem)
        if fn is None:
            return None
        return fn(profile)

    def _coerce_for_field(self, value: Any, field: DetectedField) -> Any:
        if field.kind == "checkbox":
            return bool(value)
        if field.kind in {"select", "radio"} and field.options:
            return _best_option(str(value), field.options)
        if field.kind == "number":
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        return value

    def _ai_map(self, profile: CandidateProfile, fields: list[DetectedField]) -> list[FieldMapping]:
        if not self.client.enabled:
            return []
        payload = self.client.chat_json(
            FIELD_MAPPING_SYSTEM,
            field_mapping_user(
                profile.model_dump_json(),
                json.dumps([f.model_dump() for f in fields]),
            ),
        )
        if not payload or "mappings" not in payload:
            return []

        out: list[FieldMapping] = []
        for item in payload.get("mappings", []):
            try:
                m = FieldMapping.model_validate(item)
            except ValidationError as e:
                log.warning("Dropping malformed AI mapping: %s", e)
                continue
            f = next((x for x in fields if x.selector == m.selector), None)
            if f is None:
                continue
            coerced = self._coerce_for_field(m.value, f)
            if coerced is None:
                continue
            out.append(
                FieldMapping(
                    selector=m.selector,
                    semantic=f.semantic if f.semantic != "unknown" else m.semantic,
                    value=coerced,
                    confidence=min(max(m.confidence, 0.0), 1.0),
                    reason=m.reason or "ai",
                )
            )
        return out


def _best_option(value: str, options: list[str]) -> Optional[str]:
    v = value.strip().lower()
    if not v:
        return None
    for o in options:
        if o.strip().lower() == v:
            return o
    for o in options:
        lo = o.strip().lower()
        if v in lo or lo in v:
            return o
    return None


def _pick_yes_no(field: DetectedField, *, want_yes: bool) -> Any:
    if field.kind == "checkbox":
        return want_yes
    target = "yes" if want_yes else "no"
    return _best_option(target, field.options) or target
