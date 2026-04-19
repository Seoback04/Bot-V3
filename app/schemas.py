"""Pydantic data contracts — single source of truth for structured data."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Education(BaseModel):
    model_config = ConfigDict(extra="ignore")
    degree: str
    institution: str
    year: Optional[int] = None


class WorkExperience(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str
    company: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class ProjectItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    description: Optional[str] = None
    url: Optional[str] = None


class CandidateProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    years_of_experience: Optional[float] = None
    work_authorization: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    work_experience: list[WorkExperience] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    summary: Optional[str] = None
    preferred_job_titles: list[str] = Field(default_factory=list)


FieldKind = Literal[
    "text", "email", "tel", "url", "number", "textarea",
    "select", "radio", "checkbox", "file", "date", "unknown",
]

SemanticLabel = Literal[
    "full_name", "first_name", "last_name", "email", "phone",
    "address", "city", "state", "country", "postal_code",
    "linkedin", "github", "portfolio", "website",
    "cover_letter", "summary",
    "resume_upload", "portfolio_upload",
    "years_of_experience", "current_title", "current_company",
    "preferred_job_title", "salary_expectation", "start_date",
    "work_authorization", "visa_sponsorship",
    "education_degree", "education_institution",
    "skills", "certifications",
    "gender", "ethnicity", "veteran_status", "disability_status",
    "consent", "unknown",
]


class DetectedField(BaseModel):
    model_config = ConfigDict(extra="ignore")

    selector: str
    kind: FieldKind
    name: Optional[str] = None
    id: Optional[str] = None
    label: Optional[str] = None
    placeholder: Optional[str] = None
    aria_label: Optional[str] = None
    options: list[str] = Field(default_factory=list)
    required: bool = False
    disabled: bool = False
    semantic: SemanticLabel = "unknown"
    classification_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class FieldMapping(BaseModel):
    model_config = ConfigDict(extra="ignore")

    selector: str
    semantic: SemanticLabel
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    reason: Optional[str] = None


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    selector: str
    semantic: SemanticLabel
    expected: Any
    actual: Any = None
    status: Literal["ok", "mismatch", "skipped", "error"]
    message: Optional[str] = None


class RunReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    started_at: datetime
    finished_at: Optional[datetime] = None
    url: str
    submit_attempted: bool = False
    submit_succeeded: bool = False
    profile_summary: dict[str, Any] = Field(default_factory=dict)
    detected_fields: list[DetectedField] = Field(default_factory=list)
    mappings: list[FieldMapping] = Field(default_factory=list)
    validations: list[ValidationResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    screenshot_path: Optional[str] = None
    dom_snapshot_path: Optional[str] = None
