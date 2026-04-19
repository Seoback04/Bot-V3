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

## CI/CD pipeline
The project ships with a GitHub Actions workflow at `.github/workflows/ci.yml` that enforces quality on every push and pull request to `main`.
### What runs
- **Matrix build**: `ubuntu-latest` and `windows-latest`, Python `3.11` and `3.12` (4 combinations).
- **Dependency install**: `pip install -r requirements.txt` with pip cache keyed on the lockfile.
- **Browser install**: `python -m playwright install --with-deps chromium` so the Playwright integration test runs for real in CI.
- **Byte-compile**: `python -m compileall -q app config main.py` catches syntax errors before tests.
- **Full test suite**: `pytest -v --maxfail=1` runs all 33 unit + integration tests under `HEADLESS=true`.
- **Artifacts**: `outputs/` (logs, screenshots, DOM snapshots, run reports) is uploaded per matrix cell with 7-day retention for post-mortem.
### Pipeline guarantees
- PRs cannot merge to `main` if any matrix cell fails (enable branch protection → "Require status checks" → select the `Test (...)` checks).
- `concurrency` cancels superseded runs on the same ref to keep CI fast.
- `workflow_dispatch` lets you trigger manual reruns from the Actions tab.
### Local equivalent
Run what CI runs, locally:
```bash
python -m compileall -q app config main.py
pytest -v --maxfail=1
```
### Release / deployment flow
The current project is a portable Python package with no hosted surface to deploy. The recommended release path is:
1. Tag a commit on `main` (`git tag v0.1.0 && git push --tags`).
2. Add a `release` job to the workflow triggered on tag push that builds a wheel via `python -m build` and attaches it to a GitHub Release.
3. Optionally publish to a private index (Artifactory, GitHub Packages) or PyPI with `pypa/gh-action-pypi-publish` and trusted publishing.
## Limitations
- Captcha/anti-bot walls are out of scope.
- OAuth/SSO apply flows are out of scope.
- Bot never submits unless `ALLOW_REAL_SUBMIT=true` AND `--submit` are both set.
- AI mapping is probabilistic; low-confidence fields are flagged, not hidden.
## Scalability roadmap
The current codebase is a single-machine, linear pipeline. The following changes graduate it to a scalable, multi-tenant service without discarding the existing architecture.
### Concurrency and throughput
- **Async Playwright**: swap the sync `PlaywrightBase` for `async_playwright` behind the same interface to run N applications in parallel per process.
- **Worker pool**: introduce a queue (Redis + RQ, Celery, or Temporal) where each job is `{profile_id, url, submit_flag}` and workers pull, run, and report.
- **Browser context pooling**: keep a warm pool of authenticated `BrowserContext` objects per portal to amortize cold-start cost.
### Storage and state
- **Profiles in a database**: move `CandidateProfile` from flat JSON to Postgres with the Pydantic schema mapped via SQLModel/SQLAlchemy. Enables versioning, multi-user, and audit trails.
- **Run reports in object storage**: write `RunReport` JSON, screenshots, and DOM snapshots to S3/GCS/Azure Blob, with presigned URLs in a metadata row.
- **Structured metrics**: emit OpenTelemetry spans per phase (scan, classify, map, fill, validate) and ship to Grafana/Datadog for per-portal success-rate dashboards.
### Resilience and observability
- **Circuit breakers** per portal host so a single broken site doesn't burn budget.
- **Dead-letter queue** for runs that exhaust retries; include the DOM snapshot so a human can triage.
- **Replayable runs**: persist the `list[DetectedField]` and mapping decisions so a failing run can be replayed deterministically against a saved DOM snapshot.
### Portal-specific accuracy
- **Per-portal adapter plug-ins**: `GreenhouseAdapter`, `LeverAdapter`, `WorkdayAdapter`, each overriding selectors and multi-step wizard flow while reusing `PlaywrightBase` and the scoring/validation layer.
- **Vector-backed field mapper**: embed labels + context and retrieve few-shot examples at map time to lift accuracy on novel fields.
- **Human-in-the-loop**: a lightweight review UI (FastAPI + HTMX) that renders proposed mappings and lets the user confirm or edit before fill. Every correction becomes labeled training data.
### Security and multi-tenancy
- **Secret isolation**: per-user encrypted `OPENAI_API_KEY` via a KMS; never log secrets.
- **PII minimization**: redact email/phone/address from logs by default; keep full fidelity only in the encrypted run report.
- **RBAC**: split roles into `applicant`, `reviewer`, `admin` so enterprise deployments can gate `ALLOW_REAL_SUBMIT` per role.
- **Rate limiting and politeness**: per-host request budgets with jittered backoff to respect target sites.
### Packaging and deployment
- **Container image**: multi-stage Dockerfile with `mcr.microsoft.com/playwright/python` as the base so browsers are preinstalled.
- **Helm chart / Compose**: deploy a queue, a worker pool, an API, and a review UI as separate services.
- **Horizontal autoscaling**: scale worker replicas on queue depth; keep a minimum of 1 to preserve the warm browser pool.

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
