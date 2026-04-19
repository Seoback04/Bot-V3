"""Unit tests for deterministic field classification."""
from __future__ import annotations

from app.browser.field_detector import FieldDetector
from app.schemas import DetectedField


def _make(selector, kind="text", **kw) -> DetectedField:
    return DetectedField(selector=selector, kind=kind, **kw)


def test_email_kind_wins():
    out = FieldDetector().classify([_make("#e", kind="email", label="Contact")])
    assert out[0].semantic == "email"
    assert out[0].classification_confidence >= 0.9


def test_first_name_by_label():
    out = FieldDetector().classify([_make("#fn", label="First Name")])
    assert out[0].semantic == "first_name"


def test_last_name_by_placeholder():
    out = FieldDetector().classify([_make("#ln", placeholder="Surname")])
    assert out[0].semantic == "last_name"


def test_linkedin_vs_github_url():
    a = _make("#a", kind="url", label="LinkedIn URL")
    b = _make("#b", kind="url", label="GitHub profile")
    out = FieldDetector().classify([a, b])
    assert out[0].semantic == "linkedin"
    assert out[1].semantic == "github"


def test_resume_upload_file_input():
    out = FieldDetector().classify([_make("#cv", kind="file", label="Upload your CV")])
    assert out[0].semantic == "resume_upload"


def test_years_of_experience():
    out = FieldDetector().classify([_make("#yoe", label="Years of experience")])
    assert out[0].semantic == "years_of_experience"


def test_consent_checkbox():
    out = FieldDetector().classify([_make("#c", kind="checkbox", label="I agree to the Privacy Policy")])
    assert out[0].semantic == "consent"


def test_unknown_remains_unknown_without_ai():
    out = FieldDetector().classify([_make("#x", label="Favorite color")])
    assert out[0].semantic == "unknown"


def test_radio_visa_sponsorship():
    f = _make("#v", kind="radio", label="Do you require visa sponsorship?", options=["Yes", "No"])
    out = FieldDetector().classify([f])
    assert out[0].semantic == "visa_sponsorship"
