"""
Browser/Reddit source — runs tasks/reddit.py live and returns the resulting JSON.

This is a thin wrapper that exists so orchestrator plans can invoke a live
browser scrape from a unified interface. Costs $0.30-1.00 per call (Sonnet 4.5)
and takes 8-13 min wall time per the vault docs.

Returns the parsed RA dict (same shape as a results/reddit_*.json file). The
orchestrator then funnels it through adapters/to_pulse.convert() like any
other source.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


async def _run_async(subreddits: list[str], queries: list[str], max_threads: int) -> dict:
    """Invoke tasks/reddit.run() and read back the JSON it just wrote."""
    from tasks import reddit as reddit_task   # local import: lazy + fail-loud only when used
    out_path = await reddit_task.run(subreddits=subreddits, queries=queries, max_threads=max_threads)
    return json.loads(Path(out_path).read_text(encoding="utf-8"))


def run(subreddits: list[str], queries: list[str], max_threads: int = 1) -> dict:
    """Synchronous entry for the orchestrator. Blocks for the duration of
    the browser scrape (long). Returns the RA Reddit results dict."""
    return asyncio.run(_run_async(subreddits, queries, max_threads))
