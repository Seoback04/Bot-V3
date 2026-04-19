"""Classify DetectedFields: heuristics + AI fallback."""
from __future__ import annotations

import json
import re
from typing import Optional

from app.ai.openai_client import OpenAIClient
from app.ai.prompts import FIELD_CLASSIFICATION_SYSTEM, field_classification_user
from app.logger import get_logger
from app.schemas import DetectedField, SemanticLabel


log = get_logger(__name__)


_HEURISTICS: list[tuple[str, SemanticLabel]] = [
    (r"first.?name|given.?name|fname", "first_name"),
    (r"last.?name|family.?name|surname|lname", "last_name"),
    (r"full.?name|your.?name|applicant.?name|candidate.?name|^name$", "full_name"),
    (r"e[-\s]?mail", "email"),
    (r"phone|mobile|contact.?number|tel", "phone"),
    (r"linkedin", "linkedin"),
    (r"github", "github"),
    (r"portfolio|personal.?site", "portfolio"),
    (r"website|url", "website"),
    (r"city", "city"),
    (r"state|province", "state"),
    (r"country", "country"),
    (r"zip|postal", "postal_code"),
    (r"address|street", "address"),
    (r"cover.?letter", "cover_letter"),
    (r"summary|about.?you|bio", "summary"),
    (r"resume|cv", "resume_upload"),
    (r"years.{0,3}experience|yrs.?exp|exp.*years", "years_of_experience"),
    (r"current.?title|current.?role|job.?title", "current_title"),
    (r"current.?company|employer", "current_company"),
    (r"preferred.?title|desired.?role|role.?interest", "preferred_job_title"),
    (r"salary|compensation|expected.?pay", "salary_expectation"),
    (r"start.?date|available.?from|availability", "start_date"),
    (r"work.?auth|authorization|eligible.*work", "work_authorization"),
    (r"visa|sponsor", "visa_sponsorship"),
    (r"degree", "education_degree"),
    (r"school|university|institution", "education_institution"),
    (r"skill", "skills"),
    (r"certific", "certifications"),
    (r"gender", "gender"),
    (r"ethnic|race", "ethnicity"),
    (r"veteran", "veteran_status"),
    (r"disab", "disability_status"),
    (r"consent|agree|terms|privacy", "consent"),
]


class FieldDetector:
    def __init__(self, client: Optional[OpenAIClient] = None) -> None:
        self.client = client or OpenAIClient()

    def classify(self, fields: list[DetectedField]) -> list[DetectedField]:
        for f in fields:
            sem, conf = _heuristic_label(f)
            f.semantic = sem
            f.classification_confidence = conf

        unknown = [f for f in fields if f.semantic == "unknown"]
        if unknown and self.client.enabled:
            self._ai_classify(unknown, fields)
        return fields

    def _ai_classify(self, unknown: list[DetectedField], all_fields: list[DetectedField]) -> None:
        payload = self.client.chat_json(
            FIELD_CLASSIFICATION_SYSTEM,
            field_classification_user(json.dumps([u.model_dump() for u in unknown])),
        )
        if not payload or "classifications" not in payload:
            return
        index = {f.selector: f for f in all_fields}
        for item in payload["classifications"]:
            try:
                sel = str(item["selector"])
                sem = str(item["semantic"])
                conf = float(item.get("confidence", 0.0))
            except (KeyError, TypeError, ValueError):
                continue
            f = index.get(sel)
            if f is None or f.semantic != "unknown":
                continue
            f.semantic = sem  # type: ignore[assignment]
            f.classification_confidence = max(0.0, min(1.0, conf))


def _heuristic_label(field: DetectedField) -> tuple[SemanticLabel, float]:
    haystack = " ".join(
        (x or "").lower()
        for x in (field.label, field.aria_label, field.placeholder, field.name, field.id)
    )

    if field.kind == "file":
        if re.search(r"resume|cv", haystack):
            return "resume_upload", 0.95
        if re.search(r"portfolio", haystack):
            return "portfolio_upload", 0.9
        return "resume_upload", 0.6

    if field.kind == "email":
        return "email", 0.98
    if field.kind == "tel":
        return "phone", 0.95
    if field.kind == "url":
        if "linkedin" in haystack:
            return "linkedin", 0.95
        if "github" in haystack:
            return "github", 0.95
        return "website", 0.8
    if field.kind == "date":
        if "start" in haystack or "avail" in haystack:
            return "start_date", 0.9
        return "start_date", 0.55

    for pattern, label in _HEURISTICS:
        if re.search(pattern, haystack):
            return label, 0.88

    return "unknown", 0.0
