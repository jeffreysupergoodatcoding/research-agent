"""
Pulse adapter — converts Research Agent task outputs to Pulse PostRecord JSONL.

Maps each Research Agent schema to Pulse's PostRecord format and writes a JSONL
file ready for upload via Pulse's POST /api/ingestion/upload endpoint.

Supported source shapes (Research Agent's existing outputs):
  - RedditScanOutput   → one PostRecord per (thread + each comment)
  - AmazonScanOutput   → one PostRecord per (listing + each review)
  - GoogleTrendsScanOutput → one PostRecord per keyword (treats trajectory + notes as content)

Pure function module. No HTTP calls; only file I/O. The push step (uploading to
Pulse) lives in cli.py which calls this adapter then POSTs.

PostRecord schema (target):
  {
    id, platform, entity_id, author_id (sha256 hashed),
    author_metadata, content, parent_id, created_at,
    engagement: {likes, shares, replies, views},
    url, raw
  }
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def _sha256(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_relative_or_now(s: str | None) -> str:
    """Pulse needs a real ISO timestamp. Reddit posted_relative ('2 days ago')
    can't be reliably parsed without context — fall back to scrape time."""
    if not s:
        return _utc_now_iso()
    # If it's already ISO-ish, pass through
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError):
        return _utc_now_iso()


# ---------------------------------------------------------------------------
# Reddit  →  PostRecord
# ---------------------------------------------------------------------------

def reddit_to_post_records(reddit_output: dict, entity_id: str = "") -> Iterable[dict]:
    """Yield one PostRecord per thread-OP and per comment.

    Thread OP becomes a top-level post; each comment becomes a child with
    parent_id pointing to the thread OP.
    """
    for thread in reddit_output.get("threads", []):
        url = thread.get("url") or ""
        thread_id = f"reddit:{_sha256(url)[:16]}"

        # Thread OP
        op_content = (thread.get("title") or "").strip()
        body = (thread.get("body") or "").strip()
        if body:
            op_content = f"{op_content}\n\n{body}".strip()

        if op_content:
            yield {
                "id": thread_id,
                "platform": "reddit",
                "entity_id": entity_id,
                "author_id": _sha256(thread.get("author") or "anonymous"),
                "author_metadata": {
                    "username": thread.get("author") or "",
                    "subreddit": thread.get("subreddit") or "",
                },
                "content": op_content,
                "parent_id": None,
                "created_at": _parse_relative_or_now(thread.get("posted_relative")),
                "engagement": {
                    "likes": int(thread.get("score") or 0),
                    "shares": 0,
                    "replies": int(thread.get("num_comments_reported") or 0),
                    "views": 0,
                },
                "url": url,
                "raw": {
                    "source": "research_agent.reddit",
                    "subreddit": thread.get("subreddit"),
                    "posted_relative": thread.get("posted_relative"),
                },
            }

        # Comments — one PostRecord each, parent_id pointing at thread OP
        for i, c in enumerate(thread.get("comments", [])):
            body = (c.get("body") or "").strip()
            if not body:
                continue
            comment_id = f"reddit:{_sha256(url + str(i) + body[:50])[:16]}"
            yield {
                "id": comment_id,
                "platform": "reddit",
                "entity_id": entity_id,
                "author_id": _sha256(c.get("author") or "anonymous"),
                "author_metadata": {
                    "username": c.get("author") or "",
                    "subreddit": thread.get("subreddit") or "",
                },
                "content": body,
                "parent_id": thread_id,
                "created_at": _parse_relative_or_now(c.get("posted_relative")),
                "engagement": {
                    "likes": int(c.get("score") or 0),
                    "shares": 0,
                    "replies": 0,
                    "views": 0,
                },
                "url": url,
                "raw": {
                    "source": "research_agent.reddit.comment",
                    "posted_relative": c.get("posted_relative"),
                },
            }


# ---------------------------------------------------------------------------
# Amazon  →  PostRecord
# ---------------------------------------------------------------------------

def amazon_to_post_records(amazon_output: dict, entity_id: str = "") -> Iterable[dict]:
    """Yield one PostRecord per listing (description+bullets) and per review."""
    for listing in amazon_output.get("listings", []):
        url = listing.get("url") or ""
        asin = listing.get("asin") or _sha256(url)[:10]
        listing_id = f"amazon:{asin}"

        # Listing description = title + bullets + description
        parts = [listing.get("title") or ""]
        for b in listing.get("bullets") or []:
            parts.append(f"• {b}")
        if listing.get("description"):
            parts.append(listing["description"])
        listing_content = "\n".join(p for p in parts if p).strip()

        if listing_content:
            yield {
                "id": listing_id,
                "platform": "amazon",
                "entity_id": entity_id,
                "author_id": _sha256(listing.get("brand") or "amazon-listing"),
                "author_metadata": {
                    "brand": listing.get("brand") or "",
                    "asin": asin,
                    "price": listing.get("price"),
                    "list_price": listing.get("list_price"),
                    "discount_pct": listing.get("discount_pct"),
                    "rating": listing.get("aggregate_rating"),
                    "ratings_count": listing.get("global_ratings_count"),
                },
                "content": listing_content,
                "parent_id": None,
                "created_at": _utc_now_iso(),
                "engagement": {
                    "likes": int(listing.get("global_ratings_count") or 0),
                    "shares": 0,
                    "replies": 0,
                    "views": 0,
                },
                "url": url,
                "raw": {
                    "source": "research_agent.amazon.listing",
                    "star_distribution_pct": listing.get("star_distribution_pct") or {},
                },
            }

        # Reviews
        for i, r in enumerate(listing.get("reviews") or []):
            body = (r.get("body") or "").strip()
            if not body:
                continue
            title = (r.get("title") or "").strip()
            content = f"{title}\n\n{body}".strip() if title else body
            yield {
                "id": f"amazon:{asin}:rev:{i}",
                "platform": "amazon",
                "entity_id": entity_id,
                "author_id": _sha256(r.get("reviewer") or f"reviewer_{i}"),
                "author_metadata": {
                    "reviewer": r.get("reviewer") or "",
                    "verified_purchase": bool(r.get("verified_purchase")),
                    "vine": bool(r.get("vine")),
                    "rating": r.get("rating"),
                },
                "content": content,
                "parent_id": listing_id,
                "created_at": _parse_relative_or_now(r.get("date")),
                "engagement": {
                    "likes": int(r.get("helpful_count") or 0),
                    "shares": 0,
                    "replies": 0,
                    "views": 0,
                },
                "url": url,
                "raw": {
                    "source": "research_agent.amazon.review",
                    "rating": r.get("rating"),
                    "date": r.get("date"),
                },
            }


# ---------------------------------------------------------------------------
# Google Trends  →  PostRecord
# ---------------------------------------------------------------------------

def trends_to_post_records(trends_output: dict, entity_id: str = "") -> Iterable[dict]:
    """One PostRecord per keyword. Treats the keyword + trajectory + notes as
    a 'category-momentum signal' for Pulse downstream."""
    for t in trends_output.get("trends", []):
        kw = (t.get("keyword") or "").strip()
        if not kw:
            continue

        # Compose a content string Pulse's text-based pipeline can read
        parts = [
            f"[Google Trends] {kw}",
            f"Trajectory: {t.get('trajectory') or 'unknown'}",
        ]
        if t.get("interest_now") is not None:
            parts.append(f"Current interest: {t['interest_now']}/100")
        if t.get("interest_avg_estimate") is not None:
            parts.append(f"Estimated avg: {t['interest_avg_estimate']:.1f}")
        if t.get("notes"):
            parts.append(t["notes"])
        if t.get("related_rising"):
            parts.append(f"Rising related: {', '.join(t['related_rising'])}")
        if t.get("related_top"):
            parts.append(f"Top related: {', '.join(t['related_top'])}")
        content = " · ".join(p for p in parts if p)

        # Engagement proxy: interest_now (0-100 scale → use as a 'likes-like' value)
        eng_proxy = int(t.get("interest_now") or 0)

        yield {
            "id": f"trends:{_sha256(kw)[:16]}",
            "platform": "google_trends",
            "entity_id": entity_id,
            "author_id": _sha256("google_trends"),
            "author_metadata": {
                "geo": t.get("geo") or "US",
                "timeframe": t.get("timeframe") or "",
            },
            "content": content,
            "parent_id": None,
            "created_at": _utc_now_iso(),
            "engagement": {
                "likes": eng_proxy,
                "shares": 0,
                "replies": 0,
                "views": 0,
            },
            "url": "",
            "raw": {
                "source": "research_agent.trends",
                "keyword": kw,
                "trajectory": t.get("trajectory"),
                "related_rising": t.get("related_rising") or [],
                "related_top": t.get("related_top") or [],
            },
        }


# ---------------------------------------------------------------------------
# Top-level dispatcher
# ---------------------------------------------------------------------------

def convert(ra_output: dict, entity_id: str = "") -> list[dict]:
    """Auto-detect Research Agent output shape and produce PostRecord list.

    Detection: looks at top-level keys. RA outputs all have a "task" field plus
    one of {threads, listings, trends}.
    """
    task = ra_output.get("task", "").lower()
    if task == "reddit" or "threads" in ra_output:
        return list(reddit_to_post_records(ra_output, entity_id))
    if task == "amazon" or "listings" in ra_output:
        return list(amazon_to_post_records(ra_output, entity_id))
    if task == "trends" or task == "google_trends" or "trends" in ra_output:
        return list(trends_to_post_records(ra_output, entity_id))
    raise ValueError(
        f"Unrecognized Research Agent output shape. "
        f"task={task!r}, top-level keys={list(ra_output.keys())}"
    )


def write_jsonl(records: list[dict], out_path: Path) -> int:
    """Write PostRecords to a JSONL file. Returns count written."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    return len(records)
