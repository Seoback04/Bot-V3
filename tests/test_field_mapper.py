"""Unit tests for FieldMapper, OpenAI mocked."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.ai.field_mapper import FieldMapper
from app.schemas import CandidateProfile, DetectedField


def _profile() -> CandidateProfile:
    return CandidateProfile(
        full_name="Jane Doe",
        email="jane@example.com",
        phone="+14155550199",
        location="San Francisco, CA, USA",
        linkedin="https://linkedin.com/in/janedoe",
        github="https://github.com/janedoe",
        portfolio="https://janedoe.dev",
        years_of_experience=6,
        work_authorization="US Citizen",
        skills=["Python", "Playwright"],
        preferred_job_titles=["SDET"],
        summary="SDET",
    )


def _ai_disabled() -> MagicMock:
    c = MagicMock()
    c.enabled = False
    c.chat_json.return_value = None
    return c


def test_deterministic_mapping_basic():
    fields = [
        DetectedField(selector="#fn", kind="text", semantic="first_name"),
        DetectedField(selector="#ln", kind="text", semantic="last_name"),
        DetectedField(selector="#em", kind="email", semantic="email"),
        DetectedField(selector="#ph", kind="tel", semantic="phone"),
        DetectedField(selector="#li", kind="url", semantic="linkedin"),
        DetectedField(selector="#gh", kind="url", semantic="github"),
    ]
    m = FieldMapper(client=_ai_disabled()).map(_profile(), fields)
    vals = {x.selector: x.value for x in m}
    assert vals["#fn"] == "Jane"
    assert vals["#ln"] == "Doe"
    assert vals["#em"] == "jane@example.com"
    assert vals["#ph"] == "+14155550199"
    assert "linkedin" in vals["#li"]
    assert "github" in vals["#gh"]


def test_select_option_coerced():
    fields = [DetectedField(
        selector="#role", kind="select", semantic="preferred_job_title",
        options=["QA Automation Engineer", "SDET", "Frontend Engineer"],
    )]
    m = FieldMapper(client=_ai_disabled()).map(_profile(), fields)
    assert m[0].value == "SDET"


def test_disabled_field_skipped():
    fields = [DetectedField(selector="#em", kind="email", semantic="email", disabled=True)]
    assert FieldMapper(client=_ai_disabled()).map(_profile(), fields) == []


def test_checkbox_consent():
    fields = [DetectedField(selector="#c", kind="checkbox", semantic="consent")]
    m = FieldMapper(client=_ai_disabled()).map(_profile(), fields)
    assert m[0].value is True


def test_visa_sponsorship_for_citizen_picks_no():
    fields = [DetectedField(
        selector="#v", kind="radio", semantic="visa_sponsorship", options=["Yes", "No"],
    )]
    m = FieldMapper(client=_ai_disabled()).map(_profile(), fields)
    assert m[0].value == "No"


def test_resume_upload_uses_resume_file_path():
    fields = [DetectedField(selector="#cv", kind="file", semantic="resume_upload")]
    m = FieldMapper(client=_ai_disabled(), resume_file_path="/tmp/resume.pdf").map(_profile(), fields)
    assert m[0].value == "/tmp/resume.pdf"


def test_ai_fallback_merged_for_unknown_fields():
    fields = [DetectedField(selector="#fav", kind="text", semantic="unknown")]
    mocked = MagicMock()
    mocked.enabled = True
    mocked.chat_json.return_value = {
        "mappings": [
            {"selector": "#fav", "semantic": "summary", "value": "Loves testing",
             "confidence": 0.7, "reason": "guess"}
        ]
    }
    m = FieldMapper(client=mocked).map(_profile(), fields)
    assert len(m) == 1
    assert m[0].value == "Loves testing"
    assert m[0].confidence == 0.7


def test_ai_malformed_is_ignored():
    fields = [DetectedField(selector="#x", kind="text", semantic="unknown")]
    mocked = MagicMock()
    mocked.enabled = True
    mocked.chat_json.return_value = {"mappings": [{"nope": True}]}
    assert FieldMapper(client=mocked).map(_profile(), fields) == []
