"""Aggregate autofill validation summarizer."""
from __future__ import annotations

from dataclasses import dataclass

from app.logger import get_logger
from app.models import LOW_CONFIDENCE_THRESHOLD
from app.schemas import FieldMapping, ValidationResult


log = get_logger(__name__)


@dataclass
class ValidationSummary:
    total: int
    ok: int
    mismatched: int
    skipped: int
    errored: int
    warnings: list[str]

    @property
    def success_rate(self) -> float:
        return (self.ok / self.total) if self.total else 0.0


class AutofillValidator:
    def summarize(
        self,
        mappings: list[FieldMapping],
        results: list[ValidationResult],
    ) -> ValidationSummary:
        by_selector = {m.selector: m for m in mappings}
        ok = mm = sk = er = 0
        warnings: list[str] = []

        for r in results:
            if r.status == "ok":
                ok += 1
            elif r.status == "mismatch":
                mm += 1
            elif r.status == "skipped":
                sk += 1
            elif r.status == "error":
                er += 1

            m = by_selector.get(r.selector)
            if m and m.confidence < LOW_CONFIDENCE_THRESHOLD:
                warnings.append(
                    f"low-confidence mapping for {r.semantic} (selector={r.selector}, "
                    f"confidence={m.confidence:.2f})"
                )
            if r.status == "mismatch":
                warnings.append(
                    f"mismatch on {r.semantic} (selector={r.selector}): "
                    f"expected={r.expected!r} actual={r.actual!r}"
                )

        summary = ValidationSummary(
            total=len(results), ok=ok, mismatched=mm, skipped=sk, errored=er, warnings=warnings,
        )
        log.info(
            "Validation summary: total=%d ok=%d mismatch=%d skipped=%d error=%d rate=%.2f",
            summary.total, summary.ok, summary.mismatched, summary.skipped,
            summary.errored, summary.success_rate,
        )
        return summary
