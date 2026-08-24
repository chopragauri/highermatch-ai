import os
from dotenv import load_dotenv

# Loads backend/.env into the process environment. Previously this app relied on
# vars being exported manually in the shell before starting uvicorn — .env existed
# only as a template nobody actually read. This is what makes a real .env file work.
load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

# Only email addresses on these domains may register as HR — a @yahoo.com address is
# mandatory for HR accounts; every other domain registers as a candidate by default
# (candidate registration has no domain restriction). This allowlist is the actual
# gate, enforced server-side in routers/auth.py, not just a checkbox in the UI.
ALLOWED_HR_EMAIL_DOMAINS = [
    d.strip().lower()
    for d in os.getenv("ALLOWED_HR_EMAIL_DOMAINS", "yahoo.com").split(",")
    if d.strip()
]

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
    if o.strip()
]

# Optional: when set, match summaries are enhanced with a natural-language rewrite
# from Groq's fast LLM inference. Entirely optional — if unset, empty, or the call
# fails for any reason (no network, rate limit, timeout), matching falls back to the
# deterministic local template summary, so the app never loses its offline guarantee.
# Optional: LLM-based resume parsing (OpenCode Go, OpenAI-compatible). When unset or
# unreachable, parsing falls back to the deterministic rule-based parser. Read via
# config rather than os.environ directly so importing the parser is enough to pick up
# .env — reading os.environ at call time silently saw no key in scripts and tests that
# hadn't imported this module first.
OPENCODE_API_KEY = os.getenv("OPENCODE_API_KEY", "").strip()
OPENCODE_BASE_URL = os.getenv("OPENCODE_BASE_URL", "https://opencode.ai/zen/go/v1")
OPENCODE_MODEL = os.getenv("OPENCODE_MODEL", "deepseek-v4-flash")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
# Verify a model is live on your account before changing this — Groq deprecates and
# rotates model IDs, and a stale ID fails with a 404 that the fallback silently
# swallows (looks like "the LLM just isn't working"). List them via client.models.list().
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
