"""Reddit scan task. See PLAN.md §Tasks → Reddit."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import config
from agent.browser_agent import ResearchAgent
from agent.parsers import parse_reddit_markdown
from agent.storage import save


def _build_prompt(subreddits: list[str], queries: list[str], max_threads: int) -> str:
    template = (config.PROMPTS_DIR / "reddit.md").read_text()
    pairs = [(s, q) for s in subreddits for q in queries]
    pairs_text = "\n".join(f"  - r/{s} :: \"{q}\"" for s, q in pairs)
    return (
        f"{template}\n\n"
        f"INPUTS:\n{pairs_text}\n"
        f"max_threads_per_pair: {max_threads}\n\n"
        "Visit each (subreddit, query) pair, capture up to max_threads_per_pair threads, "
        "and return them all in a single `threads` list. "
        "For each thread, expand visible 'load more comments' links once if present, "
        "then collect all comments you can see. "
        "Set num_comments_reported to the count Reddit shows, even if you couldn't expand all of them."
    )


async def run(subreddits: list[str], queries: list[str], max_threads: int = 3) -> Path:
    prompt = _build_prompt(subreddits, queries, max_threads)
    agent = ResearchAgent(model=config.MODEL, headless=config.HEADLESS)
    raw_text = await agent.run_text_task(
        prompt=prompt,
        max_steps=25,
        flash_mode=True,
    )
    parsed = parse_reddit_markdown(raw_text)
    payload = {
        "task": "reddit",
        "inputs": {"subreddits": subreddits, "queries": queries, "max_threads": max_threads},
        "thread_count": len(parsed.threads),
        "total_comments": sum(len(t.comments) for t in parsed.threads),
        "raw_text_chars": len(raw_text),
        "threads": [t.model_dump(mode="json") for t in parsed.threads],
    }
    out = save(payload, "reddit", config.RESULTS_DIR)
    # Also save the raw markdown alongside for debugging / re-parsing
    (out.parent / out.name.replace(".json", ".raw.md")).write_text(raw_text)
    return out


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--subreddits", nargs="+", default=["Preschoolers"])
    p.add_argument("--queries", nargs="+", default=["best toys for 4 year old"])
    p.add_argument("--max-threads", type=int, default=3)
    args = p.parse_args()
    out = asyncio.run(run(args.subreddits, args.queries, args.max_threads))
    print(f"\n[reddit] saved → {out}")
