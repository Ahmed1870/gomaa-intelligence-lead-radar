import re
from urllib.parse import urlparse

EMAIL_RE = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}$", re.I)
BLOCKED_LOCAL = {
    "noreply", "no-reply", "donotreply", "do-not-reply", "notifications",
    "notification", "mailer-daemon", "postmaster"
}
LOW_ROLE = {"support", "help", "customer-service", "customerservice"}
HIGH_ROLE = {
    "sales", "business", "marketing", "owner", "founder", "manager", "commercial",
    "partnerships", "partnership", "director"
}
MEDIUM_ROLE = {"contact", "hello", "admin", "info"}


def normalize_email(value):
    if not value:
        return ""
    value = value.strip().lower()
    value = value.removeprefix("mailto:").split("?", 1)[0].strip()
    return value


def classify(email):
    local = normalize_email(email).split("@", 1)[0]
    if local in BLOCKED_LOCAL:
        return "blocked", 0
    if local in HIGH_ROLE:
        return "high", 90
    if local in MEDIUM_ROLE:
        return "medium", 70
    if local in LOW_ROLE:
        return "low", 35
    return "generic", 50


def valid_syntax(email):
    return bool(EMAIL_RE.fullmatch(normalize_email(email)))


def domain_from_url(url):
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""
