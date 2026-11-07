"""All tunables in one place. Everything comes from the environment (see .env.example)."""
import os
from pathlib import Path


def _load_dotenv():
    p = Path(__file__).resolve().parent.parent / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

INFERENCE_URL = os.getenv("VULTR_INFERENCE_URL", "https://api.vultrinference.com/v1")
INFERENCE_KEY = os.getenv("VULTR_INFERENCE_API_KEY", "")
MODEL_FAST = os.getenv("TRIAGE_MODEL_FAST", "glm-5.3-flash")      # intake parsing, claim extraction
MODEL_SMART = os.getenv("TRIAGE_MODEL_SMART", "glm-5.3")          # PoC writing, retries, reviewer note
MODEL_SAFETY = os.getenv("TRIAGE_MODEL_SAFETY", "nemotron-3.5-content-safety")  # prompt-injection screen

# Must be a path the Docker daemon can bind-mount (on macOS + colima that means under $HOME).
CACHE = Path(os.getenv("TRIAGE_CACHE", Path.home() / ".cache" / "triage"))
DB_PATH = Path(os.getenv("TRIAGE_DB", Path(__file__).resolve().parent.parent / "triage.db"))

SANDBOX_IMAGE = os.getenv("TRIAGE_SANDBOX_IMAGE", "python:3.12-slim")
SANDBOX_PYTHON = "3.12"            # must match the image; wheels are resolved for it
LIMIT_CPUS = "1"
LIMIT_MEMORY = "512m"
LIMIT_PIDS = "128"
LIMIT_SECONDS = int(os.getenv("TRIAGE_LIMIT_SECONDS", "60"))
MAX_ATTEMPTS = 3
MAX_REPORT_CHARS = 20_000
MAX_QUEUE = 5
