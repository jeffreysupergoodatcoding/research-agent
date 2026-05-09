"""Smoke test: agent navigates to playper.com, reports page title + H1.
Confirms browser-use + Claude + Chromium wiring before any real task."""
from __future__ import annotations
import asyncio
import os
from dotenv import load_dotenv
from browser_use import Agent, BrowserProfile, ChatAnthropic

load_dotenv()


async def main() -> None:
    headless = os.getenv("HEADLESS", "false").lower() == "true"
    model = os.getenv("RESEARCH_MODEL", "claude-sonnet-4-5-20250929")

    print(f"[smoke] model={model}  headless={headless}")

    llm = ChatAnthropic(model=model)
    profile = BrowserProfile(headless=headless)

    agent = Agent(
        task=(
            "Go to https://playper.com . "
            "Read the page title (browser tab title) and the main hero headline (the largest text on screen). "
            "Return them as: TITLE=<title> | H1=<hero text>. Then stop."
        ),
        llm=llm,
        browser_profile=profile,
        use_vision=True,
        max_actions_per_step=3,
    )
    result = await agent.run(max_steps=10)
    print("\n=== SMOKE RESULT ===")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
