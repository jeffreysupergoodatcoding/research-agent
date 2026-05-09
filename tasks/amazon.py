"""Amazon listing + review scan. See PLAN.md §Tasks → Amazon."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import config
from agent.browser_agent import ResearchAgent
from agent.schemas import AmazonScanOutput
from agent.storage import save


def _build_prompt(search_terms: list[str], asins: list[str], max_listings: int) -> str:
    template = (config.PROMPTS_DIR / "amazon.md").read_text()
    terms_text = "\n".join(f"  - search: \"{t}\"" for t in search_terms)
    asins_text = "\n".join(f"  - asin: {a}" for a in asins) if asins else "  (none)"
    return (
        f"{template}\n\n"
        f"INPUTS:\n"
        f"search_terms:\n{terms_text}\n"
        f"asins:\n{asins_text}\n"
        f"max_listings_total: {max_listings}\n\n"
        "Open each input source, extract the listing + reviews into your memory, "
        "and after all sources are done, emit the full list once via `done` with the structured output."
    )


async def run(
    search_terms: list[str] | None = None,
    asins: list[str] | None = None,
    max_listings: int = 2,
) -> Path:
    search_terms = search_terms or []
    asins = asins or []
    prompt = _build_prompt(search_terms, asins, max_listings)
    agent = ResearchAgent(model=config.MODEL, headless=config.HEADLESS)
    result: AmazonScanOutput = await agent.run_task(
        prompt=prompt,
        output_schema=AmazonScanOutput,
        max_steps=40,
    )
    payload = {
        "task": "amazon",
        "inputs": {"search_terms": search_terms, "asins": asins, "max_listings": max_listings},
        "listing_count": len(result.listings),
        "total_reviews": sum(len(l.reviews) for l in result.listings),
        "listings": [l.model_dump(mode="json") for l in result.listings],
    }
    return save(payload, "amazon", config.RESULTS_DIR)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--search", nargs="*", default=["melissa and doug castle playset"])
    p.add_argument("--asins", nargs="*", default=[])
    p.add_argument("--max-listings", type=int, default=2)
    args = p.parse_args()
    out = asyncio.run(run(args.search, args.asins, args.max_listings))
    print(f"\n[amazon] saved → {out}")
