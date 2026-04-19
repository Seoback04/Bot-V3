"""Unit tests for the Pydantic data contracts."""
from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas import (
    CandidateProfile,
    DetectedField,
    FieldMapping,
    RunReport,
    ValidationResult,
)


def test_candidate_profile_minimal():
    p = CandidateProfile(full_name="Jane Doe")
    assert p.full_name == "Jane Doe"
    assert p.skills == [] and p.education == []


def test_candidate_profile_rich_roundtrip():
    data = {
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "skills": ["Python", "Playwright"],
        "education": [{"degree": "BS", "institution": "UC", "year": 2018}],
        "work_experience": [{"title": "SDET", "company": "Acme"}],
        "projects": [{"name": "Bot"}],
        "certifications": ["ISTQB"],
    }
    p = CandidateProfile.model_validate(data)
    assert CandidateProfile.model_validate(p.model_dump()) == p


def test_candidate_profile_requires_full_name():
    with pytest.raises(ValidationError):
        CandidateProfile.model_validate({"email": "x@y.z"})


def test_detected_field_defaults():
    f = DetectedField(selector="#email", kind="email")
    assert f.semantic == "unknown"
    assert f.classification_confidence == 0.0


def test_detected_field_invalid_kind_rejected():
    with pytest.raises(ValidationError):
        DetectedField(selector="#x", kind="banana")  # type: ignore[arg-type]


def test_field_mapping_confidence_bounds():
    FieldMapping(selector="#a", semantic="email", value="x@y.z", confidence=0.0)
    FieldMapping(selector="#a", semantic="email", value="x@y.z", confidence=1.0)
    with pytest.raises(ValidationError):
        FieldMapping(selector="#a", semantic="email", value="x", confidence=1.5)


def test_validation_result_status_enum():
    vr = ValidationResult(selector="#a", semantic="email", expected="x", actual="x", status="ok")
    assert vr.status == "ok"
    with pytest.raises(ValidationError):
        ValidationResult(selector="#a", semantic="email", expected="x", status="weird")  # type: ignore[arg-type]


def test_run_report_defaults():
    r = RunReport(started_at=datetime.utcnow(), url="http://x")
    assert r.detected_fields == [] and r.mappings == []
