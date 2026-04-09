import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PARSED_DIR = DATA_DIR / "parsed"
TRANSLATED_DIR = DATA_DIR / "translated"
CACHE_DIR = DATA_DIR / "cache"
DIST_DIR = PROJECT_ROOT / "dist"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
INDEX_FILE = DATA_DIR / "index.json"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "x-ai/grok-4.20-beta")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

BASE_URL = "https://www.paulgraham.com"
ARTICLES_URL = f"{BASE_URL}/articles.html"
INDEX_URL = f"{BASE_URL}/index.html"

PROMPT_VERSION = "v1"
STYLE_CONFIG = "natural_fluent_chinese"
SEGMENT_SCHEMA_VERSION = "v1"

for d in [RAW_DIR, PARSED_DIR, TRANSLATED_DIR, CACHE_DIR, DIST_DIR]:
    d.mkdir(parents=True, exist_ok=True)
