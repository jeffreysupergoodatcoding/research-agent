"""JSON output helpers."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel


def save(obj: BaseModel | dict | list, name_prefix: str, results_dir: Path) -> Path:
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = results_dir / f"{name_prefix}_{ts}.json"
    if isinstance(obj, BaseModel):
        data = obj.model_dump(mode="json")
    else:
        data = obj
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return path
