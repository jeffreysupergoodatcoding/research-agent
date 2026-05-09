"""
Existing-JSON source — load a previously-scraped Research Agent results file.

Useful for:
  - Replaying historical scrapes through new adapters
  - Testing orchestration logic without paying for a fresh browser run
  - Combining a fresh Pulse-API pull with a cached browser scrape

Phase 1.5 uses this as a stand-in for live browser scrapes during orchestrator
testing so end-to-end flow can be exercised without an 8-13min browser run.
"""
from __future__ import annotations

import json
from pathlib import Path


def load(path: str) -> dict:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"existing_json source: {p}")
    return json.loads(p.read_text(encoding="utf-8"))
