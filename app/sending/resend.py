import os
import requests


def send(to, subject, html, reply_to=None, idempotency_key=None):
    key = os.environ["RESEND_API_KEY"]
    from_email = os.environ["FROM_EMAIL"]
    payload = {"from": from_email, "to": [to], "subject": subject, "html": html}
    if reply_to:
        payload["reply_to"] = reply_to
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    r = requests.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"Resend {r.status_code}: {r.text[:500]}")
    return r.json()
