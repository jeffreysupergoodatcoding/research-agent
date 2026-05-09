# Standalone Research Agent — Validation Plan (2026-05-09)

Goal: prove the extracted standalone repo `research-agent/` works for every capability we built, ending with a Playper-relevant pull.

## Phases

### A. Static health check (~2 min, no LLM cost)
1. Confirm git remote + branch + clean tree
2. Confirm Python imports resolve in the new repo (no Playper-coupled paths)
3. Confirm `.env` has `ANTHROPIC_API_KEY`
4. Confirm `BrowserProfile` stealth settings present in `agent/browser_agent.py`
5. Confirm `RawTextOutput` + `parse_reddit_markdown` exist
6. Confirm `tasks/{reddit,amazon,trends,tiktok,general}.py` import cleanly
7. Confirm `sources/{pulse_api,browser_reddit,existing_json}.py` import cleanly
8. Confirm `adapters/to_pulse.py` import + signature

### B. Wiring smoke test (~30 sec, ~$0.02)
- Run `smoke_test.py` → expect TITLE+H1 from playper.com

### C. Per-task functional tests (~25-35 min total, ~$3-5)
**One task at a time, headless, caffeinate -is, fail-fast on errors.**

- C1. Reddit: 1 Playper-relevant thread → `r/Preschoolers` "best toys for 4 year old" — confirms the markdown-emit refactor still works post-extraction.
- C2. Amazon: 1 Playper-relevant competitor listing → search "melissa and doug castle" — confirms structured emit + list_price/discount fix.
- C3. Trends: 4 Playper IP/category keywords → confirms structured emit + step budget OK.

### D. Orchestrator test (~5 min, ~$0.50)
- D1. Run `cli.py orchestrate` with a 2-task plan: 1 `existing_json` (replay Reddit JSON from C1) + 1 `pulse_api` task (skip if no Pulse server up locally — fall back to `existing_json` for both).
- Verify combined PostRecord JSONL is well-formed and ready for upload.

### E. Playper connection back-channel (~5 min, no LLM cost)
- E1. Create `clients/playper.yaml` (defaults for subreddits, search terms, trends keywords)
- E2. Add an "uplink" helper that copies the latest `results/*.json` into a place a Playper / Fragment Labs consumer can read
- E3. Verify the Playper folder can read the new results

### F. Final integrated test (~10 min, ~$1.50)
- A single Playper-themed end-to-end run that exercises browser scrape + adapter conversion + on-disk output landing in Playper's reachable workspace.

### G. Document
- Append results to Obsidian Build Log
- Update Index status table
- If a fix was needed, write up in 05 Known Issues

## Failure protocol
- If any phase fails: log, attempt the most localized fix, retry once, proceed if recovered, ABORT and report if not.
- Don't let one stuck capability block the others — phases C1-C3 are independent.

## Cost guardrail
- Hard cap: ~$10 total LLM. If we trip multiple full-budget runs, abort and ask.
