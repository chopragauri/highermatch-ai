import os
from dotenv import load_dotenv

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
