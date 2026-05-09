"""Pydantic schemas for structured agent output. Filled in during build phase."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RedditComment(BaseModel):
    author: str
    posted_relative: Optional[str] = None
    score: Optional[int] = None
    body: str


class RedditThread(BaseModel):
    url: str
    subreddit: str
    title: str
    body: Optional[str] = None
    author: Optional[str] = None
    posted_relative: Optional[str] = None
    score: Optional[int] = None
    num_comments_reported: Optional[int] = None
    comments: list[RedditComment] = []


class AmazonReview(BaseModel):
    reviewer: str
    rating: float
    title: str
    date: Optional[str] = None
    verified_purchase: bool = False
    vine: bool = False
    helpful_count: int = 0
    body: str


class AmazonListing(BaseModel):
    url: str
    asin: Optional[str] = None
    title: str
    brand: Optional[str] = None
    price: Optional[float] = None
    list_price: Optional[float] = None
    discount_pct: Optional[int] = None
    aggregate_rating: Optional[float] = None
    global_ratings_count: Optional[int] = None
    star_distribution_pct: dict[int, int] = {}
    bullets: list[str] = []
    description: Optional[str] = None
    reviews: list[AmazonReview] = []


class GoogleTrend(BaseModel):
    keyword: str
    timeframe: str
    geo: str = "US"
    interest_now: Optional[int] = None
    interest_avg_estimate: Optional[float] = None
    trajectory: str
    related_rising: list[str] = []
    related_top: list[str] = []
    notes: Optional[str] = None


class GoogleTrendsScanOutput(BaseModel):
    trends: list[GoogleTrend]


class TikTokPost(BaseModel):
    url: str
    creator: str
    caption: Optional[str] = None
    likes: Optional[int] = None
    comments_count: Optional[int] = None
    shares: Optional[int] = None
    posted_relative: Optional[str] = None
    transcript_or_summary: Optional[str] = None


class RawTextOutput(BaseModel):
    """Single-string envelope for tasks that post-parse markdown in Python.
    Avoids deep-JSON validation loops on emit."""
    raw_text: str


class RedditScanOutput(BaseModel):
    threads: list[RedditThread]


class AmazonScanOutput(BaseModel):
    listings: list[AmazonListing]


class TikTokScanOutput(BaseModel):
    posts: list[TikTokPost]


class ResearchRun(BaseModel):
    task: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    inputs: dict
    raw_log_path: Optional[str] = None
    output_path: str
