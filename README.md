# AI Resume Job Apply Bot

AI-assisted browser automation that parses resumes, extracts a structured candidate profile, maps that profile onto arbitrary web job application forms, autofills with confidence scoring, validates read-back, captures evidence, and stops **before** final submit by default.

Built as a serious portfolio project for SDET / QA automation roles.

## Why it matters

Job application forms are inconsistent and fragile. Hardcoded selector scripts break. This project combines:

- Deterministic DOM scanning (labels, aria, placeholders, names, ids).
- AI-backed classification and mapping (OpenAI) with Pydantic-validated outputs.
- Fill-then-verify autofill with per-field confidence scoring.
- Safe-submit gating (env flag + CLI flag must both be true).
- Observable runs: JSON run report, rotating log file, screenshots, optional DOM snapshot.

## Architecture

```
CLI (Typer)
 ├── ProfileService
 │    ├── FileExtractors (PDF / DOCX / TXT)
 │    └── ResumeParser (OpenAI) → Pydantic CandidateProfile
 └── ApplicationService
      ├── PlaywrightBase (lifecycle, retries, locator utils)
      ├── PageScanner       (DOM metadata)
      ├── FieldDetector     (heuristics, AI fallback)
      ├── FieldMapper       (profile → fields, confidence)
      ├── FormFiller        (type/select/check/upload + read-back)
      ├── AutofillValidator (summarize + warnings)
      └── Screenshotter     (evidence)
 └── ReportService (structured JSON report)
```

See `docs/architecture.md` for details.

## Tech stack

Python 3.11+, Playwright (sync), OpenAI SDK, Pydantic v2, Typer, pytest, logging, python-dotenv, pypdf, python-docx.

### Sync vs async Playwright

Sync API. Single-machine, linear control flow; easier to read, test, and demo. Async would pay off only under heavy concurrency, which this project does not need.

## Installation

```bash
git clone https://github.com/Seoback04/Bot-V3.git
cd Bot-V3

python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
python -m playwright install chromium
```

## Environment setup

```bash
# Windows:
copy .env.example .env
# macOS/Linux:
# cp .env.example .env
# then set OPENAI_API_KEY
```

Supported env vars:

- `OPENAI_API_KEY` — optional. Without it, deterministic fallbacks are used.
- `OPENAI_MODEL` — defaults to `gpt-4o-mini`.
- `HEADLESS` — `true`/`false` (default `false`).
- `ALLOW_REAL_SUBMIT` — hard gate on final submission. Default `false`.
- `LOG_LEVEL` — e.g. `INFO`, `DEBUG`.
- `OUTPUT_DIR` — defaults to `outputs`.

## Usage

```bash
# Parse resume only
python main.py parse-resume --resume data/sample_resume.txt

# Apply with a resume
python main.py apply --resume data/sample_resume.txt --url http://localhost:8000/local_job_application_form.html

# Apply with a pre-parsed profile
python main.py apply --profile data/sample_candidate_profile.json --url http://localhost:8000/local_job_application_form.html

# Explicitly disable submit (default)
python main.py apply --resume data/sample_resume.txt --url <URL> --no-submit

# Serve the local demo form
python main.py demo-local-form
```

## Sample outputs

- Structured profile: `data/sample_candidate_profile.json`
- Run report: `outputs/run_report_<timestamp>.json`
- Screenshot: `outputs/screenshot_review_<timestamp>.png`
- Log file: `outputs/run.log`

## Testing

```bash
pytest -v
```

Coverage:

- `test_schemas.py` — Pydantic contracts.
- `test_field_detector.py` — deterministic classification.
- `test_field_mapper.py` — mapping with mocked AI.
- `test_validator.py` — validation summary scoring.
- `test_playwright_base.py` — hermetic lifecycle + retry.
- `test_local_form_integration.py` — Playwright end-to-end against the local demo form.

## Limitations

- Captcha/anti-bot walls are out of scope.
- OAuth/SSO apply flows are out of scope.
- Bot never submits unless `ALLOW_REAL_SUBMIT=true` AND `--submit` are both set.
- AI mapping is probabilistic; low-confidence fields are flagged, not hidden.

## Future improvements

- Multi-step wizard support.
- Per-portal adapters (Greenhouse, Lever, Workday shims).
- UI for reviewing mappings before fill.
- Few-shot examples for field mapping.

## Screenshots

_Add screenshots of the demo form being autofilled here._

## Ethical / safe-use disclaimer

Intended to assist a human applicant with their own applications. Do not use to spam employers, impersonate others, bypass ToS, or submit fraudulent information. Default config stops before submit.

## Portfolio positioning — resume bullets

- Built an AI-assisted Playwright automation system that parsed resumes, mapped candidate data to web forms, and validated autofill accuracy through structured confidence scoring and field-level verification.
- Engineered a modular Python QA automation project with schema-driven data extraction, intelligent field detection, screenshot evidence capture, and JSON run reporting for job application workflows.
- Designed and tested a safe-submit browser automation framework with unit and integration coverage, resilient selector handling, and observable failure logging for professional-grade form automation.

## License

MIT. See `LICENSE`.
