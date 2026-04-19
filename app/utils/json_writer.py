"""Safe JSON serialization helpers."""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any


def _default(o: Any) -> Any:
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if hasattr(o, "model_dump"):
        return o.model_dump()
    if hasattr(o, "__dict__"):
        return vars(o)
    return str(o)


def dumps(obj: Any, indent: int = 2) -> str:
    return json.dumps(obj, default=_default, indent=indent, ensure_ascii=False)


def write_json(path: str | Path, obj: Any, indent: int = 2) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(dumps(obj, indent=indent), encoding="utf-8")
    return p


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))
