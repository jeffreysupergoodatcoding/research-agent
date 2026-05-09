"""Source wrappers — each module is a thin client around one data source.

  - pulse_api      → triggers Pulse's existing /api/ingestion/* endpoints
  - browser_reddit → wraps tasks/reddit.py (live browser scrape)
  - browser_amazon → wraps tasks/amazon.py
  - browser_trends → wraps tasks/trends.py
  - existing_json  → load a previously-scraped Research Agent results file

The orchestrator (Phase 2) picks among these per its plan. Phase 1.5 ships
pulse_api + existing_json so the orchestration logic can be exercised
end-to-end without requiring a live 8-13 minute browser scrape on every test.
"""
