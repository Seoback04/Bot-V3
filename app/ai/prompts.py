"""Prompt templates. All return strict JSON."""
from __future__ import annotations


RESUME_TO_PROFILE_SYSTEM = """\
You are a resume parsing assistant. Output ONLY a single JSON object that
conforms to the CandidateProfile schema. No prose, no markdown fences.

Schema (all optional except full_name):
- full_name (string, required)
- email, phone, location, linkedin, github, portfolio, summary (string|null)
- years_of_experience (number|null)
- work_authorization (string|null)
- skills (string[])
- education ([{degree, institution, year?}])
- work_experience ([{title, company, start_date?, end_date?, description?}])
- projects ([{name, description?, url?}])
- certifications (string[])
- preferred_job_titles (string[])

Infer years_of_experience from dates when possible. Use null for unknown scalars
and [] for unknown arrays. Never invent employers or schools. JSON only.
"""


def resume_to_profile_user(resume_text: str) -> str:
    return f"RESUME_TEXT:\n{resume_text}\n\nReturn the JSON object now."


FIELD_CLASSIFICATION_SYSTEM = """\
You classify form fields. For each field, return one of the allowed semantic
labels. Output ONLY:

{"classifications": [{"selector": "...", "semantic": "...", "confidence": 0.0-1.0}]}

Allowed labels: full_name, first_name, last_name, email, phone, address, city,
state, country, postal_code, linkedin, github, portfolio, website,
cover_letter, summary, resume_upload, portfolio_upload, years_of_experience,
current_title, current_company, preferred_job_title, salary_expectation,
start_date, work_authorization, visa_sponsorship, education_degree,
education_institution, skills, certifications, gender, ethnicity,
veteran_status, disability_status, consent, unknown.

If uncertain, use "unknown" with low confidence. JSON only.
"""


def field_classification_user(fields_json: str) -> str:
    return f"FIELDS:\n{fields_json}\n\nReturn the JSON object now."


FIELD_MAPPING_SYSTEM = """\
You map candidate profile data onto detected form fields.

Rules:
- For each field with a resolvable mapping, emit:
  {"selector","semantic","value","confidence","reason"}
- Omit unmappable fields.
- For select/radio, pick the exact option string whose text best matches.
- For checkbox, value must be boolean.
- For file uploads, value must be an absolute file path or omit.
- For name fields, split full_name into first/last when needed.
- For phone, use digits and optional leading '+'.

Output ONLY: {"mappings": [ ... ]}  JSON only.
"""


def field_mapping_user(profile_json: str, fields_json: str) -> str:
    return (
        f"CANDIDATE_PROFILE:\n{profile_json}\n\n"
        f"DETECTED_FIELDS:\n{fields_json}\n\n"
        f"Return the JSON object now."
    )
