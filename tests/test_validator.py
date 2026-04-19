"""Unit tests for AutofillValidator."""
from __future__ import annotations

from app.browser.validator import AutofillValidator
from app.schemas import FieldMapping, ValidationResult


def test_summary_counts_and_warnings():
    mappings = [
        FieldMapping(selector="#a", semantic="email", value="x@y.z", confidence=0.9),
        FieldMapping(selector="#b", semantic="phone", value="+1", confidence=0.4),
        FieldMapping(selector="#c", semantic="full_name", value="J D", confidence=0.8),
        FieldMapping(selector="#d", semantic="skills", value="Py", confidence=0.9),
    ]
    results = [
        ValidationResult(selector="#a", semantic="email", expected="x@y.z", actual="x@y.z", status="ok"),
        ValidationResult(selector="#b", semantic="phone", expected="+1", actual="+2", status="mismatch"),
        ValidationResult(selector="#c", semantic="full_name", expected="J D", status="skipped"),
        ValidationResult(selector="#d", semantic="skills", expected="Py", status="error", message="boom"),
    ]
    s = AutofillValidator().summarize(mappings, results)
    assert s.total == 4 and s.ok == 1 and s.mismatched == 1
    assert s.skipped == 1 and s.errored == 1
    assert any("low-confidence" in w for w in s.warnings)
    assert any("mismatch on phone" in w for w in s.warnings)
    assert 0.0 <= s.success_rate <= 1.0
