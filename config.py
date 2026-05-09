import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = os.getenv("RESEARCH_MODEL", "claude-sonnet-4-5-20250929")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
RESULTS_DIR = Path(os.getenv("RESULTS_DIR", ROOT / "results"))
PROMPTS_DIR = ROOT / "prompts"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
