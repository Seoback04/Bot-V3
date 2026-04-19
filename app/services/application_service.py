"""Orchestrates the full apply run."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from app.ai.field_mapper import FieldMapper
from app.ai.openai_client import OpenAIClient
from app.browser.field_detector import FieldDetector
from app.browser.form_filler import FormFiller
from app.browser.page_scanner import PageScanner
from app.browser.playwright_base import PlaywrightBase
from app.browser.screenshotter import Screenshotter
from app.browser.validator import AutofillValidator
from app.exceptions import SubmitBlockedError
from app.logger import get_logger
from app.schemas import CandidateProfile, RunReport
from config.settings import SETTINGS


log = get_logger(__name__)


class ApplicationService:
    def __init__(
        self,
        client: Optional[OpenAIClient] = None,
        output_dir: Optional[Path] = None,
    ) -> None:
        self.client = client or OpenAIClient()
        self.output_dir = Path(output_dir or SETTINGS.output_dir)

    def run(
        self,
        profile: CandidateProfile,
        url: str,
        *,
        submit: bool = False,
        resume_file_path: Optional[str] = None,
        headless: Optional[bool] = None,
    ) -> RunReport:
        report = RunReport(
            started_at=datetime.utcnow(),
            url=url,
            profile_summary={
                "full_name": profile.full_name,
                "email": profile.email,
                "location": profile.location,
                "years_of_experience": profile.years_of_experience,
            },
        )

        scanner = PageScanner()
        detector = FieldDetector(client=self.client)
        mapper = FieldMapper(client=self.client, resume_file_path=resume_file_path)
        validator = AutofillValidator()
        shotter = Screenshotter(self.output_dir)

        try:
            with PlaywrightBase(headless=headless) as browser:
                browser.goto(url)

                fields = scanner.scan(browser)
                fields = detector.classify(fields)
                report.detected_fields = fields

                mappings = mapper.map(profile, fields)
                report.mappings = mappings

                filler = FormFiller(browser)
                results = filler.fill_all(fields, mappings)
                report.validations = results

                summary = validator.summarize(mappings, results)
                report.warnings.extend(summary.warnings)

                png, html_path = shotter.capture(browser, tag="review")
                if png:
                    report.screenshot_path = str(png)
                if html_path:
                    report.dom_snapshot_path = str(html_path)

                if submit:
                    self._maybe_submit(browser, report)
        except SubmitBlockedError as e:
            report.errors.append(str(e))
            log.error("Submit blocked: %s", e)
        except Exception as e:
            report.errors.append(f"{type(e).__name__}: {e}")
            log.exception("Apply run failed")
        finally:
            report.finished_at = datetime.utcnow()
        return report

    def _maybe_submit(self, browser: PlaywrightBase, report: RunReport) -> None:
        if not SETTINGS.allow_real_submit:
            raise SubmitBlockedError("ALLOW_REAL_SUBMIT is false; refusing to click final submit.")
        candidates = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Apply")',
        ]
        for sel in candidates:
            btn = browser.page.locator(sel).first
            if btn.count() and btn.is_visible():
                report.submit_attempted = True
                log.warning("Clicking submit: %s", sel)
                btn.click()
                browser.page.wait_for_load_state("networkidle", timeout=15000)
                report.submit_succeeded = True
                return
        raise SubmitBlockedError("No submit button found.")
