"""TikTok trend scan via browser-use."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import config
from agent.browser_agent import ResearchAgent
from agent.schemas import TikTokScanOutput
from agent.storage import save


def _build_prompt(hashtags: list[str], queries: list[str], max_posts: int) -> str:
    template = (config.PROMPTS_DIR / "tiktok.md").read_text()
    h_text = "\n".join(f"  - #{h}" for h in hashtags) if hashtags else "  (none)"
    q_text = "\n".join(f"  - \"{q}\"" for q in queries) if queries else "  (none)"
    return (
        f"{template}\n\n"
        f"INPUTS:\n"
        f"hashtags:\n{h_text}\n"
        f"search_queries:\n{q_text}\n"
        f"max_posts_total: {max_posts}\n"
    )


async def run(
    hashtags: list[str] | None = None,
    queries: list[str] | None = None,
    max_posts: int = 10,
) -> Path:
    hashtags = hashtags or []
    queries = queries or []
    prompt = _build_prompt(hashtags, queries, max_posts)
    agent = ResearchAgent(model=config.MODEL, headless=config.HEADLESS)
    result: TikTokScanOutput = await agent.run_task(
        prompt=prompt,
        output_schema=TikTokScanOutput,
        max_steps=40,
    )
    payload = {
        "task": "tiktok",
        "inputs": {"hashtags": hashtags, "queries": queries, "max_posts": max_posts},
        "post_count": len(result.posts),
        "posts": [p.model_dump(mode="json") for p in result.posts],
    }
    return save(payload, "tiktok", config.RESULTS_DIR)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--hashtags", nargs="*", default=[])
    p.add_argument("--queries", nargs="*", default=[])
    p.add_argument("--max-posts", type=int, default=10)
    args = p.parse_args()
    out = asyncio.run(run(args.hashtags, args.queries, args.max_posts))
    print(f"\n[tiktok] saved → {out}")
