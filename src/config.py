import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")

HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
SLOW_MO = int(os.getenv("SLOW_MO", "100"))
MAX_STEPS = int(os.getenv("MAX_STEPS", "20"))
SCREENSHOT_DIR = BASE_DIR / os.getenv("SCREENSHOT_DIR", "demo/task-traces")

USE_MOCK_LLM = not bool(OPENAI_API_KEY)

# Cost tracking
COST_PER_1K_VISION_TOKENS = float(os.getenv("COST_PER_1K_VISION_TOKENS", "0.01"))
TOKENS_PER_SCREENSHOT = int(os.getenv("TOKENS_PER_SCREENSHOT", "1000"))

# Test store
TEST_STORE_PATH = BASE_DIR / "test-store" / "index.html"
