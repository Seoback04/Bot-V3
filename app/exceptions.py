"""Typed exception hierarchy."""
from __future__ import annotations


class AppError(Exception):
    """Base class for all project-specific errors."""


class ResumeExtractionError(AppError):
    """Resume file cannot be read or parsed to text."""


class AIError(AppError):
    """AI layer failure that could not be recovered."""


class SchemaValidationError(AppError):
    """AI output failed Pydantic validation after salvage attempts."""


class BrowserError(AppError):
    """Browser automation step failed after retries."""


class SubmitBlockedError(AppError):
    """Submission was requested but safety gates disallow it."""
