"""
Pulse API source — Research Agent triggers Pulse's existing ingestion endpoints
instead of duplicating the work. Pulse handles HN / Twitter / RSS / YouTube /
Reddit-PRAW; Research Agent just calls and waits.

Net result: the Pulse corpus on disk grows the same way it would if a Pulse
user clicked the UI — but the trigger comes from the agent's plan instead of
a human.

This module does NOT call browser-use. It's pure HTTP.
"""
from __future__ import annotations

import json
import time
import urllib.request
from typing import Any


def _post(url: str, body: dict, timeout: int = 60) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(url: str, timeout: int = 60) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class PulseAPI:
    """Thin client around Pulse's REST endpoints."""

    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Entity management
    # ------------------------------------------------------------------

    def list_entities(self) -> list[dict]:
        return _get(f"{self.base}/api/graph/entities")

    def get_entity(self, entity_id: str) -> dict:
        return _get(f"{self.base}/api/graph/entities/{entity_id}")

    def create_entity(self, name: str, entity_type: str = "topic",
                      description: str = "", keywords: list[str] | None = None) -> dict:
        return _post(f"{self.base}/api/graph/entities", {
            "name": name,
            "entity_type": entity_type,
            "description": description,
            "keywords": keywords or [],
        })

    # ------------------------------------------------------------------
    # Ingestion — orchestrator's main lever
    # ------------------------------------------------------------------

    def pull(self, entity_id: str, sources: list[dict], limit: int = 200) -> str:
        """Trigger /api/ingestion/pull. Returns task_id (async)."""
        body = _post(f"{self.base}/api/ingestion/pull", {
            "entity_id": entity_id,
            "sources": sources,
            "limit": limit,
        })
        return body["task_id"]

    def auto_pull(self, entity_id: str, limit: int = 200,
                  extra_terms: list[str] | None = None) -> str:
        """Trigger /api/ingestion/auto-pull (Pulse picks sources automatically)."""
        body = _post(f"{self.base}/api/ingestion/auto-pull", {
            "entity_id": entity_id,
            "limit": limit,
            "extra_terms": extra_terms or [],
        })
        return body["task_id"]

    def wait_for_task(self, task_id: str, poll_interval: int = 2,
                      timeout: int = 600) -> dict:
        """Poll /api/ingestion/status until completed/error."""
        elapsed = 0
        last_progress = -1
        while elapsed < timeout:
            status = _get(f"{self.base}/api/ingestion/status/{task_id}")
            prog = status.get("progress", 0)
            if prog != last_progress:
                last_progress = prog
            if status.get("status") in ("completed", "error", "stopped"):
                return status
            time.sleep(poll_interval)
            elapsed += poll_interval
        raise TimeoutError(f"Pulse ingestion task {task_id} timed out after {timeout}s")

    def upload_jsonl(self, entity_id: str, jsonl_path: str) -> dict:
        """POST /api/ingestion/upload (multipart). Used for browser-scraped data."""
        import mimetypes
        import secrets
        from pathlib import Path

        boundary = "----RA-" + secrets.token_hex(16)
        crlf = b"\r\n"
        body = bytearray()
        for k, v in [("entity_id", entity_id), ("file_format", "jsonl")]:
            body += f"--{boundary}".encode() + crlf
            body += f'Content-Disposition: form-data; name="{k}"'.encode() + crlf + crlf
            body += str(v).encode() + crlf

        path = Path(jsonl_path)
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body += f"--{boundary}".encode() + crlf
        body += f'Content-Disposition: form-data; name="file"; filename="{path.name}"'.encode() + crlf
        body += f"Content-Type: {ctype}".encode() + crlf + crlf
        body += path.read_bytes() + crlf
        body += f"--{boundary}--".encode() + crlf

        req = urllib.request.Request(
            f"{self.base}/api/ingestion/upload",
            data=bytes(body),
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body)),
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))


# Convenience module-level instance
def client(base_url: str | None = None) -> PulseAPI:
    return PulseAPI(base_url or "http://localhost:5001")
