import json
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.validation.email import normalize_email, valid_syntax

EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", re.I)
PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
SOCIALS = {
    "linkedin": ("linkedin.com",),
    "facebook": ("facebook.com",),
    "instagram": ("instagram.com",),
    "whatsapp": ("wa.me", "whatsapp.com"),
}
CARD_HINT = re.compile(r"(?:company|business|listing|supplier|vendor|merchant|organization|result|directory|profile|card|item)", re.I)


def _blank(base_url):
    return {
        "name": "",
        "website": base_url,
        "emails": set(),
        "phones": set(),
        "linkedin": "",
        "facebook": "",
        "instagram": "",
        "whatsapp": "",
    }


def _merge_from_soup(soup, base_url):
    out = _blank(base_url)
    title = soup.find(["h1", "title"])
    if title:
        out["name"] = title.get_text(" ", strip=True)[:180]

    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"].strip())
        low = href.lower()
        if low.startswith("mailto:"):
            e = normalize_email(href[7:])
            if valid_syntax(e):
                out["emails"].add(e)
        elif low.startswith("tel:"):
            out["phones"].add(href[4:].strip()[:40])
        else:
            for key, hosts in SOCIALS.items():
                if not out[key] and any(host in low for host in hosts):
                    out[key] = href

    text = soup.get_text(" ", strip=True)
    for e in EMAIL_PATTERN.findall(text):
        e = normalize_email(e)
        if valid_syntax(e):
            out["emails"].add(e)
    for p in PHONE_PATTERN.findall(text):
        out["phones"].add(p[:40])

    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or s.get_text() or "")
        except Exception:
            continue
        objs = data if isinstance(data, list) else [data]
        for obj in objs:
            if not isinstance(obj, dict):
                continue
            if isinstance(obj.get("@graph"), list):
                objs.extend(x for x in obj["@graph"] if isinstance(x, dict))
                continue
            if obj.get("name") and not out["name"]:
                out["name"] = str(obj["name"])[:180]
            if obj.get("email"):
                e = normalize_email(str(obj["email"]))
                if valid_syntax(e):
                    out["emails"].add(e)
            if obj.get("telephone"):
                out["phones"].add(str(obj["telephone"])[:40])
            if obj.get("url"):
                out["website"] = urljoin(base_url, str(obj["url"]))
            cp = obj.get("contactPoint")
            if isinstance(cp, dict) and cp.get("email"):
                e = normalize_email(str(cp["email"]))
                if valid_syntax(e):
                    out["emails"].add(e)
    return out


def _card_score(tag):
    attrs = " ".join([
        " ".join(tag.get("class", [])),
        str(tag.get("id", "")),
        tag.name or "",
    ])
    return 1 if CARD_HINT.search(attrs) else 0


def _extract_card(tag, base_url):
    out = _blank(base_url)
    heading = tag.find(["h1", "h2", "h3", "h4", "h5", "strong", "b"])
    if heading:
        out["name"] = heading.get_text(" ", strip=True)[:180]
    for a in tag.find_all("a", href=True):
        href = urljoin(base_url, a["href"].strip())
        low = href.lower()
        if low.startswith("mailto:"):
            e = normalize_email(href[7:])
            if valid_syntax(e): out["emails"].add(e)
        elif low.startswith("tel:"):
            out["phones"].add(href[4:].strip()[:40])
        elif urlparse(href).netloc and urlparse(href).netloc != urlparse(base_url).netloc:
            for key, hosts in SOCIALS.items():
                if not out[key] and any(host in low for host in hosts): out[key] = href
        else:
            # A same-domain external link is a likely company website when the card is a directory result.
            if href != base_url and not href.startswith("#") and out["website"] == base_url:
                out["website"] = href
    text = tag.get_text(" ", strip=True)
    for e in EMAIL_PATTERN.findall(text):
        e = normalize_email(e)
        if valid_syntax(e): out["emails"].add(e)
    for p in PHONE_PATTERN.findall(text): out["phones"].add(p[:40])
    return out


def extract_many(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # Prefer structured business records when a directory exposes them.
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or s.get_text() or "")
        except Exception:
            continue
        objs = data if isinstance(data, list) else [data]
        for obj in objs:
            if not isinstance(obj, dict):
                continue
            if isinstance(obj.get("itemListElement"), list):
                for entry in obj["itemListElement"]:
                    candidate = entry.get("item") if isinstance(entry, dict) else None
                    if isinstance(candidate, dict) and (candidate.get("name") or candidate.get("email")):
                        mini = _blank(base_url)
                        mini["name"] = str(candidate.get("name", ""))[:180]
                        mini["website"] = urljoin(base_url, str(candidate.get("url", base_url)))
                        e = normalize_email(str(candidate.get("email", "")))
                        if valid_syntax(e): mini["emails"].add(e)
                        if candidate.get("telephone"): mini["phones"].add(str(candidate["telephone"])[:40])
                        results.append(mini)

    # Directory cards: only accept compact repeated blocks that actually contain an email/phone.
    candidates = []
    for tag in soup.find_all(["article", "li", "div"]):
        if not _card_score(tag):
            continue
        text = tag.get_text(" ", strip=True)
        if not EMAIL_PATTERN.search(text) and not PHONE_PATTERN.search(text) and not tag.find("a", href=re.compile(r"^mailto:", re.I)):
            continue
        if len(text) > 2500:
            continue
        candidates.append(tag)
    # Keep the smallest useful cards to avoid nesting the same listing inside larger containers.
    selected = []
    for tag in sorted(candidates, key=lambda x: len(x.get_text(" ", strip=True))):
        if any(tag in other for other in selected):
            continue
        selected.append(tag)
        if len(selected) >= 200:
            break
    for tag in selected:
        item = _extract_card(tag, base_url)
        if item["emails"] or item["phones"]:
            results.append(item)

    if results:
        # Deduplicate records by email set + normalized name.
        unique = []
        seen = set()
        for item in results:
            key = (item["name"].strip().lower(), tuple(sorted(item["emails"])))
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    # Fallback for a standalone company page.
    return [_merge_from_soup(soup, base_url)]


def extract(html, base_url):
    """Backward-compatible single-record helper."""
    return extract_many(html, base_url)[0]
