"""
Research Agent CLI — Phase 1.

Single command for Phase 1: take an existing Research Agent results JSON
(produced by the existing tasks/{reddit,amazon,trends}.py runs) and push it
into Pulse via Pulse's BYO upload endpoint.

Usage:
  python cli.py push-to-pulse \\
      --source results/reddit_20260509T055625Z.json \\
      --entity-id <pulse_entity_uuid> \\
      [--pulse-url http://localhost:5001] \\
      [--out-dir ./out_pulse_jsonl] \\
      [--dry-run]

The conversion (RA schema → PostRecord) lives in adapters/to_pulse.py and is
side-effect-free; this script wraps it with file I/O and the HTTP upload.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from adapters.to_pulse import convert, write_jsonl


def _post_multipart(url: str, fields: dict, file_path: Path, file_field: str = "file",
                    file_name: str | None = None) -> dict:
    """Stdlib-only multipart upload. Avoids adding 'requests' as a dep."""
    import mimetypes
    import secrets

    boundary = "----RA-" + secrets.token_hex(16)
    crlf = b"\r\n"
    body = bytearray()

    for k, v in fields.items():
        body += f"--{boundary}".encode() + crlf
        body += f'Content-Disposition: form-data; name="{k}"'.encode() + crlf + crlf
        body += str(v).encode() + crlf

    file_bytes = file_path.read_bytes()
    fname = file_name or file_path.name
    ctype = mimetypes.guess_type(fname)[0] or "application/octet-stream"
    body += f"--{boundary}".encode() + crlf
    body += f'Content-Disposition: form-data; name="{file_field}"; filename="{fname}"'.encode() + crlf
    body += f"Content-Type: {ctype}".encode() + crlf + crlf
    body += file_bytes + crlf
    body += f"--{boundary}--".encode() + crlf

    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode("utf-8"))


def cmd_push_to_pulse(args: argparse.Namespace) -> int:
    src = Path(args.source).expanduser().resolve()
    if not src.exists():
        print(f"ERROR: source file not found: {src}", file=sys.stderr)
        return 2

    ra_output = json.loads(src.read_text(encoding="utf-8"))
    print(f"  source       : {src}")
    print(f"  RA task      : {ra_output.get('task', '<unknown>')}")
    print(f"  RA top keys  : {list(ra_output.keys())}")

    try:
        records = convert(ra_output, entity_id=args.entity_id)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    print(f"  converted    : {len(records)} PostRecord rows")

    # Write a JSONL alongside source
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"{src.stem}_to_pulse_{ts}.jsonl"
    write_jsonl(records, out_path)
    print(f"  wrote JSONL  : {out_path}")

    if args.dry_run:
        print("  --dry-run: skipping Pulse upload")
        return 0

    if not args.entity_id:
        print("ERROR: --entity-id required when not --dry-run", file=sys.stderr)
        return 4

    upload_url = f"{args.pulse_url.rstrip('/')}/api/ingestion/upload"
    print(f"  uploading to : {upload_url}")
    try:
        result = _post_multipart(
            upload_url,
            fields={"entity_id": args.entity_id, "file_format": "jsonl"},
            file_path=out_path,
            file_name=out_path.name,
        )
    except Exception as exc:
        print(f"ERROR: upload failed: {exc}", file=sys.stderr)
        return 5

    print(f"  pulse result : added={result.get('records_added')} skipped={result.get('records_skipped')}")
    if result.get("errors"):
        print(f"  errors[{len(result['errors'])}]:")
        for e in result["errors"][:5]:
            print(f"    - {e}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Research Agent CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    push = sub.add_parser(
        "push-to-pulse",
        help="Convert a Research Agent result JSON to PostRecord JSONL and upload to Pulse.",
    )
    push.add_argument("--source", required=True, help="Path to a Research Agent results JSON")
    push.add_argument("--entity-id", default="", help="Target Pulse entity UUID")
    push.add_argument("--pulse-url", default="http://localhost:5001",
                      help="Pulse backend base URL (default: http://localhost:5001)")
    push.add_argument("--out-dir", default="./out_pulse_jsonl",
                      help="Where to write the converted JSONL (default: ./out_pulse_jsonl)")
    push.add_argument("--dry-run", action="store_true",
                      help="Convert + write JSONL but skip the upload")
    push.set_defaults(func=cmd_push_to_pulse)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
