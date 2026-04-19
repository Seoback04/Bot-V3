"""Orchestrates resume -> CandidateProfile and profile I/O."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.ai.openai_client import OpenAIClient
from app.ai.resume_parser import ResumeParser
from app.logger import get_logger
from app.schemas import CandidateProfile
from app.utils.file_extractors import extract_text
from app.utils.json_writer import read_json, write_json


log = get_logger(__name__)


class ProfileService:
    def __init__(self, client: Optional[OpenAIClient] = None) -> None:
        self.parser = ResumeParser(client=client)

    def parse_resume(self, resume_path: str | Path) -> CandidateProfile:
        text = extract_text(resume_path)
        log.info("Extracted %d chars from resume.", len(text))
        profile = self.parser.parse(text)
        log.info("Parsed profile for %s", profile.full_name)
        return profile

    def load_profile(self, profile_path: str | Path) -> CandidateProfile:
        return CandidateProfile.model_validate(read_json(profile_path))

    def save_profile(self, profile: CandidateProfile, out_path: str | Path) -> Path:
        return write_json(out_path, profile.model_dump(), indent=2)
