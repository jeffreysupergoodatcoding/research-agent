"""Core wrapper around browser-use Agent."""
from __future__ import annotations
from typing import Type, TypeVar
from pydantic import BaseModel
from browser_use import Agent, BrowserProfile, ChatAnthropic

T = TypeVar("T", bound=BaseModel)


# Realistic Chrome 147 on macOS — matches what a normal user sends.
REAL_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/147.0.0.0 Safari/537.36"
)

# Chrome launch args to suppress headless tells.
STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process,AutomationControlled",
    "--disable-dev-shm-usage",
    "--no-default-browser-check",
    "--no-first-run",
    "--password-store=basic",
    "--use-mock-keychain",
]

# Drop the default --enable-automation flag that browser-use / playwright sets.
IGNORE_DEFAULT_ARGS = ["--enable-automation"]


class ResearchAgent:
    """Thin facade so each task script doesn't reach into browser-use directly."""

    def __init__(self, model: str, headless: bool = False) -> None:
        self.model = model
        self.headless = headless

    async def run_text_task(
        self,
        prompt: str,
        max_steps: int = 25,
        max_actions_per_step: int = 2,
        vision_detail: str = "low",
        flash_mode: bool = True,
        llm_timeout: int = 180,
        max_failures: int = 8,
    ) -> str:
        """Run a task that emits a single raw-text payload for Python-side parsing.
        Avoids deep-schema bracket bugs on the LLM's `done` action."""
        from agent.schemas import RawTextOutput
        result: RawTextOutput = await self.run_task(
            prompt=prompt,
            output_schema=RawTextOutput,
            max_steps=max_steps,
            max_actions_per_step=max_actions_per_step,
            vision_detail=vision_detail,
            flash_mode=flash_mode,
            llm_timeout=llm_timeout,
            max_failures=max_failures,
        )
        return result.raw_text

    async def run_task(
        self,
        prompt: str,
        output_schema: Type[T],
        max_steps: int = 30,
        max_actions_per_step: int = 2,
        vision_detail: str = "low",
        flash_mode: bool = True,
        llm_timeout: int = 180,
        max_failures: int = 8,
    ) -> T:
        llm = ChatAnthropic(model=self.model)
        profile = BrowserProfile(
            headless=self.headless,
            user_agent=REAL_USER_AGENT,
            args=STEALTH_ARGS,
            ignore_default_args=IGNORE_DEFAULT_ARGS,
            viewport={"width": 1440, "height": 900},
        )
        agent = Agent(
            task=prompt,
            llm=llm,
            browser_profile=profile,
            output_model_schema=output_schema,
            use_vision=True,
            use_judge=False,
            max_actions_per_step=max_actions_per_step,
            vision_detail_level=vision_detail,
            flash_mode=flash_mode,
            llm_timeout=llm_timeout,
            max_failures=max_failures,
        )
        history = await agent.run(max_steps=max_steps)
        parsed = history.structured_output
        if parsed is None:
            raw = history.final_result()
            raise RuntimeError(f"Agent did not produce a structured output. final_result={raw!r}")
        return parsed
