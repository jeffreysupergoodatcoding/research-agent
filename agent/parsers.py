"""Markdown → schema parsers for tasks that emit raw text via run_text_task."""
from __future__ import annotations
import re
from typing import Iterator
from agent.schemas import RedditThread, RedditComment, RedditScanOutput


def _split_blocks(text: str, start_marker: str) -> list[str]:
    """Split text into blocks each beginning with start_marker (excluding leading prefix)."""
    parts = re.split(rf"^{re.escape(start_marker)}\s*$", text, flags=re.MULTILINE)
    # Drop preamble; rejoin marker as a sentinel for clarity (but parse on the body alone)
    return [p.strip() for p in parts[1:] if p.strip()]


def _kv(block: str) -> dict[str, str]:
    """Parse the leading KEY: value pairs from a block, until first blank line or 'BODY:'/'COMMENTS:'."""
    out: dict[str, str] = {}
    for line in block.splitlines():
        s = line.strip()
        if not s:
            break
        if s in ("BODY:", "COMMENTS:"):
            break
        m = re.match(r"^([A-Z_]+):\s*(.*)$", s)
        if not m:
            break
        out[m.group(1)] = m.group(2).strip()
    return out


def _section(block: str, label: str) -> str | None:
    """Return the multi-line value of a `LABEL:`-style section, ending before the next ALL-CAPS section header or `## ` marker."""
    pat = re.compile(rf"^{label}:\s*$", flags=re.MULTILINE)
    m = pat.search(block)
    if not m:
        return None
    start = m.end()
    # End at next bare LABEL: line or `## ` marker
    end_pat = re.compile(r"^(?:[A-Z_]+:\s*$|##\s+C\s*$)", flags=re.MULTILINE)
    e = end_pat.search(block, pos=start)
    end = e.start() if e else len(block)
    return block[start:end].strip()


def _parse_int(s: str | None) -> int | None:
    if s is None:
        return None
    m = re.search(r"-?\d+", s.replace(",", ""))
    return int(m.group()) if m else None


def parse_reddit_markdown(text: str) -> RedditScanOutput:
    """Parse the markdown contract from prompts/reddit.md into a RedditScanOutput."""
    threads: list[RedditThread] = []
    for thread_block in _split_blocks(text, "# THREAD"):
        meta = _kv(thread_block)
        body = _section(thread_block, "BODY") or ""

        # Comments live after the COMMENTS: header, split by `## C`
        comments_idx = thread_block.find("COMMENTS:")
        comments_text = thread_block[comments_idx:] if comments_idx >= 0 else ""
        comments: list[RedditComment] = []
        for c_block in _split_blocks(comments_text, "## C"):
            cmeta = _kv(c_block)
            cbody = _section(c_block, "BODY") or ""
            comments.append(RedditComment(
                author=cmeta.get("AUTHOR", "[unknown]"),
                posted_relative=cmeta.get("POSTED"),
                score=_parse_int(cmeta.get("SCORE")),
                body=cbody,
            ))

        threads.append(RedditThread(
            url=meta.get("URL", ""),
            subreddit=meta.get("SUBREDDIT", ""),
            title=meta.get("TITLE", ""),
            body=body or None,
            author=meta.get("AUTHOR"),
            posted_relative=meta.get("POSTED"),
            score=_parse_int(meta.get("SCORE")),
            num_comments_reported=_parse_int(meta.get("COMMENTS_REPORTED")),
            comments=comments,
        ))
    return RedditScanOutput(threads=threads)
