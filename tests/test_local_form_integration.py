"""Integration test against the local demo HTML form.

Skips cleanly if Playwright browsers aren't installed.
"""
from __future__ import annotations

from pathlib import Path

import pytest


pytest.importorskip("playwright.sync_api")

from app.ai.field_mapper import FieldMapper  # noqa: E402
from app.ai.openai_client import OpenAIClient  # noqa: E402
from app.browser.field_detector import FieldDetector  # noqa: E402
from app.browser.form_filler import FormFiller  # noqa: E402
from app.browser.page_scanner import PageScanner  # noqa: E402
from app.browser.playwright_base import PlaywrightBase  # noqa: E402
from app.schemas import CandidateProfile  # noqa: E402


DEMO_FORM = Path(__file__).resolve().parent.parent / "demo" / "local_job_application_form.html"


@pytest.mark.integration
def test_local_form_end_to_end(tmp_path):
    if not DEMO_FORM.exists():
        pytest.skip(f"Demo form not found: {DEMO_FORM}")

    fake_resume = tmp_path / "resume.txt"
    fake_resume.write_text("fake resume content", encoding="utf-8")

    profile = CandidateProfile(
        full_name="Jane Doe",
        email="jane@example.com",
        phone="+14155550199",
        location="San Francisco, CA, USA",
        linkedin="https://linkedin.com/in/janedoe",
        github="https://github.com/janedoe",
        portfolio="https://janedoe.dev",
        years_of_experience=6,
        work_authorization="US Citizen",
        preferred_job_titles=["SDET"],
        summary="SDET with Playwright experience.",
    )

    client = OpenAIClient()

    try:
        browser = PlaywrightBase(headless=True).start()
    except Exception as e:
        pytest.skip(f"Playwright browser not available: {e}")

    try:
        browser.goto(DEMO_FORM.as_uri())
        fields = PageScanner().scan(browser)
        assert fields, "Scanner produced no fields."
        fields = FieldDetector(client=client).classify(fields)
        semantics = {f.semantic for f in fields}
        assert "email" in semantics
        assert "first_name" in semantics or "full_name" in semantics

        mapper = FieldMapper(client=client, resume_file_path=str(fake_resume))
        mappings = mapper.map(profile, fields)
        assert mappings, "Mapper produced no mappings."

        results = FormFiller(browser).fill_all(fields, mappings)
        ok_rate = sum(1 for r in results if r.status == "ok") / max(1, len(results))
        assert ok_rate >= 0.7, f"Too many failures: ok_rate={ok_rate:.2f} results={results}"
    finally:
        browser.stop()
