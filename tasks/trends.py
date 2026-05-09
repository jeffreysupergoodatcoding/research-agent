"""Google Trends scan via browser-use."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import config
from agent.browser_agent import ResearchAgent
from agent.schemas import GoogleTrendsScanOutput
from agent.storage import save


def _build_prompt(keywords: list[str], timeframe: str, geo: str) -> str:
    template = (config.PROMPTS_DIR / "trends.md").read_text()
    kw_text = "\n".join(f"  - \"{k}\"" for k in keywords)
    return (
        f"{template}\n\n"
        f"INPUTS:\n"
        f"keywords:\n{kw_text}\n"
        f"timeframe: {timeframe}\n"
        f"geo: {geo}\n"
    )


async def run(keywords: list[str], timeframe: str = "Past 5 years", geo: str = "US") -> Path:
    prompt = _build_prompt(keywords, timeframe, geo)
    agent = ResearchAgent(model=config.MODEL, headless=config.HEADLESS)
    result: GoogleTrendsScanOutput = await agent.run_task(
        prompt=prompt,
        output_schema=GoogleTrendsScanOutput,
        max_steps=80,
    )
    payload = {
        "task": "trends",
        "inputs": {"keywords": keywords, "timeframe": timeframe, "geo": geo},
        "trend_count": len(result.trends),
        "trends": [t.model_dump(mode="json") for t in result.trends],
    }
    return save(payload, "trends", config.RESULTS_DIR)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--keywords", nargs="+", required=True)
    p.add_argument("--timeframe", default="Past 5 years")
    p.add_argument("--geo", default="US")
    args = p.parse_args()
    out = asyncio.run(run(args.keywords, args.timeframe, args.geo))
    print(f"\n[trends] saved → {out}")
