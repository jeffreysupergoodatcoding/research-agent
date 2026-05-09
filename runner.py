"""CLI entry point. Build phase wires this up."""
from __future__ import annotations
import asyncio
import typer

import config
from agent.browser_agent import ResearchAgent

app = typer.Typer(help="Playper research agent (browser-use + Claude)")


@app.command()
def reddit(
    subreddits: list[str] = typer.Option(["Preschoolers", "toddlers", "homeschool"]),
    queries: list[str] = typer.Option(["best toys for 4 year old"]),
    max_threads: int = 10,
) -> None:
    """Scan Reddit for relevant threads + comments."""
    raise typer.Exit("Not implemented yet — see PLAN.md")


@app.command()
def amazon(
    search_terms: list[str] = typer.Option(["castle playset for kids"]),
    asins: list[str] = typer.Option([]),
    max_listings: int = 5,
) -> None:
    """Scan Amazon for competitor listings + reviews."""
    raise typer.Exit("Not implemented yet — see PLAN.md")


@app.command()
def tiktok(
    hashtags: list[str] = typer.Option(["sustainabletoys", "screenfreeplay"]),
    queries: list[str] = typer.Option(["best toys for 4 year old"]),
    max_posts: int = 25,
) -> None:
    """Scan TikTok for trending toy content."""
    raise typer.Exit("Not implemented yet — see PLAN.md")


@app.command()
def research(goal: str, max_steps: int = 80) -> None:
    """Free-form research task."""
    raise typer.Exit("Not implemented yet — see PLAN.md")


if __name__ == "__main__":
    app()
