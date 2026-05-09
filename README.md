# Research Agent

Browser-use + Claude Sonnet 4.5 agent that scrapes data from sites without clean APIs (Reddit threads, Amazon listings, Google Trends, free-form research). Stealth-aware, structured Pydantic outputs.

> **Note**: this repo is the standalone extraction of the Research Agent originally built inside the Fragment Labs / Playper project. Phase 1 ships the **Pulse adapter** so this agent can feed into [Pulse](https://github.com/jeffreysupergoodatcoding/pulse) via its BYO upload endpoint, with Pulse and Fragment Labs as fully independent consumers.

---

## Architecture (two-tier)

```
┌─────────────────────────────────────────────┐
│  Research Agent  (this repo)                │
│  Tasks:  Reddit · Amazon · Trends · General │
│  Adapters:  to_pulse  ·  (to_fragment soon) │
└─────┬─────────────────────────────────┬─────┘
      │                                 │
      ▼                                 ▼
  Pulse  (BYO upload)             Fragment Labs (context layer)
  Doesn't know RA exists.         Doesn't know RA exists either.
```

**Each consumer is independent.** A Pulse run never reads Fragment's outputs and vice versa. They share the same agent codebase — improvements (better Reddit parser, better stealth) automatically benefit both — but operate on isolated `clients/<name>/` configs and write to isolated output directories.

---

## What's in Phase 1 (this version)

- ✅ All four task implementations from the original Research Agent (Reddit, Amazon, Trends, TikTok)
- ✅ Browser-use stealth flags + Sonnet 4.5 backend
- ✅ **`adapters/to_pulse.py`** — converts every RA task output to Pulse PostRecord JSONL
- ✅ **`cli.py push-to-pulse`** — single command: take an RA results JSON, upload to Pulse

What's **not** in Phase 1 (deferred to Phase 2):
- Orchestrator / planner mode (LLM decides which sources for a given simulation)
- `to_fragment` adapter
- Per-client config files (subreddits, search terms etc. still live in the existing Playper-coupled defaults)
- Auto-trigger of downstream Pulse pipelines

---

## Quick start

### 1. Install

```bash
pip3 install --user -r requirements.txt
python3 -m playwright install chromium
```

### 2. Configure

```bash
cat > .env <<'EOF'
ANTHROPIC_API_KEY=sk-ant-...
RESEARCH_MODEL=claude-sonnet-4-5-20250929
HEADLESS=false
RESULTS_DIR=./results
EOF
```

### 3. Run a task (existing workflow, unchanged)

```bash
HEADLESS=true python3 tasks/reddit.py \
    --subreddits ClaudeAI LocalLLaMA \
    --queries "Claude 4 Opus" \
    --max-threads 2

HEADLESS=true python3 tasks/amazon.py \
    --search "vision pro headset"

HEADLESS=true python3 tasks/trends.py \
    --keywords "Claude AI" "GPT-5"
```

Outputs land in `results/<task>_<timestamp>.json`.

### 4. Push to Pulse (Phase 1's new capability)

```bash
python3 cli.py push-to-pulse \
    --source ./results/reddit_20260509T055625Z.json \
    --entity-id <pulse_entity_uuid> \
    --pulse-url http://localhost:5001
```

Output:
```
  source       : /path/to/reddit_*.json
  RA task      : reddit
  converted    : 40 PostRecord rows
  wrote JSONL  : ./out_pulse_jsonl/reddit_..._to_pulse_<ts>.jsonl
  uploading to : http://localhost:5001/api/ingestion/upload
  pulse result : added=40 skipped=0
```

Add `--dry-run` to convert + write JSONL but skip the HTTP upload.

---

## Schema mapping (RA → Pulse)

| Research Agent output | Pulse PostRecord |
|---|---|
| Reddit thread | One PostRecord (`platform="reddit"`, `parent_id=None`) |
| Reddit comment | One PostRecord per comment, `parent_id` → thread ID |
| Amazon listing | One PostRecord (title + bullets + description) |
| Amazon review | One PostRecord per review, `parent_id` → listing |
| Google Trends keyword | One PostRecord per keyword (trajectory + interest_now in content) |

Author IDs are SHA-256 anonymized on the way out — no PII leaves Research Agent into Pulse.

---

## Code layout

```
research-agent/
├── adapters/
│   ├── to_pulse.py         ← Phase 1 — RA schemas → PostRecord JSONL
│   └── (to_fragment.py)    ← Phase 2
├── agent/
│   ├── browser_agent.py    ← Browser-use facade
│   ├── schemas.py          ← Pydantic outputs (RedditScanOutput, AmazonScanOutput, …)
│   ├── parsers.py          ← Markdown → schema parsers (used by Reddit task)
│   └── storage.py          ← Timestamped JSON dumps
├── tasks/
│   ├── reddit.py           ← run_text_task → markdown emit → parser
│   ├── amazon.py           ← run_task → AmazonScanOutput direct
│   ├── trends.py           ← run_task → GoogleTrendsScanOutput direct
│   ├── tiktok.py           ← Blocked by login wall (documented)
│   └── general.py          ← Free-form research (scaffolded, untested)
├── prompts/                ← One markdown prompt per task
├── clients/                ← (Phase 2) per-client config
├── results/                ← Per-run JSON dumps (gitignored)
├── out_pulse_jsonl/        ← (Phase 1) converted JSONL ready for Pulse upload (gitignored)
├── runner.py               ← Existing Typer-style task launcher
├── smoke_test.py           ← `playper.com` title/H1 sanity check
├── cli.py                  ← Phase 1 — `push-to-pulse` command
└── requirements.txt
```

---

## Cost & timing

| Task | Time | Cost (Sonnet 4.5) |
|---|---|---|
| Smoke test | 10s | ~$0.02 |
| Reddit (1 thread, ~40 comments) | 8-13 min | $0.30-1.00 |
| Amazon (1 listing, ~10 reviews) | 5-8 min | $1.00-2.00 |
| Trends (4 keywords) | 7-10 min | $0.50-1.50 |
| TikTok | 2-3 min (blocked) | ~$0.30 |

This is **meaningfully more expensive than free Pulse APIs** (HN Algolia is $0/post; Twitter v2 is $0.005/post). Use Research Agent for sources Pulse can't reach (Amazon, no-auth Reddit, Trends, niche forums) — not as a default replacement.

---

## What this is NOT

- **Not a Pulse component.** Pulse doesn't know Research Agent exists — it just receives PostRecord JSONL via its BYO upload endpoint.
- **Not a Fragment component.** Same — Fragment will receive context-layer JSON via its own adapter (Phase 2), independent from Pulse.
- **Not stateful.** Each run is a one-shot. No persistent agent memory between runs.
- **Not authenticated.** No Reddit/Amazon/TikTok login. Some sites (TikTok) are unsolvable without auth — accepted limitation.

---

## License

MIT
