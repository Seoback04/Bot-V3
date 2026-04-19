# Architecture

## Modules

- **CLI (`app/cli.py`)** — Typer entry. Parses arguments, wires services.
- **ProfileService (`app/services/profile_service.py`)** — resume -> text -> AI parse -> `CandidateProfile`.
- **ApplicationService (`app/services/application_service.py`)** — orchestrates the full browser run.
- **ReportService (`app/services/report_service.py`)** — writes the JSON run report.
- **AI layer (`app/ai/*`)** — OpenAI wrapper, prompts, resume parser, field mapper.
- **Browser layer (`app/browser/*`)** — `PlaywrightBase`, `PageScanner`, `FieldDetector`, `FormFiller`, `AutofillValidator`, `Screenshotter`.
- **Utils (`app/utils/*`)** — file extractors, text cleaner, JSON writer.
- **Schemas (`app/schemas.py`)** — Pydantic contracts (source of truth).

## Control flow

```
parse-resume:
  CLI -> ProfileService.parse(path)
          -> FileExtractors.extract_text
          -> ResumeParser.parse(text)        (AI, schema-validated)
          -> CandidateProfile JSON

apply:
  CLI -> ProfileService (load or parse)
     -> ApplicationService.run(profile, url, submit_flag)
          -> PlaywrightBase.goto(url)
          -> PageScanner.scan()              (DOM metadata)
          -> FieldDetector.classify()        (heuristic -> AI fallback)
          -> FieldMapper.map(profile)        (AI with strict JSON, fallback)
          -> FormFiller.fill_all()           (fill + read-back + retry)
          -> AutofillValidator.summarize()   (confidence policy)
          -> Screenshotter.capture()
          -> optional submit (guarded)
     -> ReportService.write(run_report)
```

## Data flow

1. Resume bytes -> text (deterministic).
2. Text -> `CandidateProfile` (AI, strict JSON, Pydantic).
3. DOM -> `list[DetectedField]` (deterministic scan).
4. Fields + profile -> `list[FieldMapping]` with confidence (deterministic + AI).
5. Fill outcomes -> `list[ValidationResult]`.
6. All above -> `RunReport`.

## Where AI is used

- Resume parsing.
- Field classification for unknowns left by heuristics.
- Profile -> field mapping top-up for still-unmapped fields.

## Where deterministic logic is used

- DOM scanning.
- Heuristic field classification (label/placeholder/aria/name/id/type).
- Value normalization (phone, URLs, booleans).
- Read-back comparison and equivalence.
- Safe-submit gating.
- Report assembly.

## Validation strategy

- Schema validation on every AI output (Pydantic). Malformed -> JSON salvage -> deterministic fallback.
- Autofill validation: re-read each control post-fill; status is `ok | mismatch | skipped | error`.
- Confidence: every mapping carries 0.0-1.0. Below LOW_CONFIDENCE_THRESHOLD -> warning.

## Failure handling

- `PlaywrightBase` wraps browser ops with bounded retry + backoff.
- AI errors never crash the run; they degrade to deterministic behavior and are logged.
- Final submit is guarded by env flag AND CLI flag. Either false -> hard stop.
- Every run (success or failure) writes a JSON report.
