"""Write structured run reports to disk."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from app.logger import get_logger
from app.schemas import RunReport
from app.utils.json_writer import write_json
from config.settings import SETTINGS


log = get_logger(__name__)


class ReportService:
    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.output_dir = Path(output_dir or SETTINGS.output_dir)

    def write(self, report: RunReport) -> Path:
        ts = (report.finished_at or datetime.utcnow()).strftime("%Y%m%dT%H%M%SZ")
        out = self.output_dir / f"run_report_{ts}.json"
        write_json(out, report.model_dump(mode="json"))
        log.info("Wrote run report: %s", out)
        return out
