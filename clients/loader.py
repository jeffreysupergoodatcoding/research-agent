"""Tiny YAML loader for client configs at clients/<name>.yaml."""
from __future__ import annotations
from pathlib import Path
import yaml


CLIENTS_DIR = Path(__file__).resolve().parent


def load(client_name: str) -> dict:
    path = CLIENTS_DIR / f"{client_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No client config at {path}")
    return yaml.safe_load(path.read_text())


def list_clients() -> list[str]:
    return sorted(p.stem for p in CLIENTS_DIR.glob("*.yaml"))
