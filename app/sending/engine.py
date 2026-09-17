import os
import time
from datetime import datetime, timezone
import yaml
from app.storage.db import connect, init_db
from app.templates import build
from app.sending.resend import send as resend_send


def cfg():
    with open("config/campaign.yml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _today():
    return datetime.now(timezone.utc).date().isoformat()


def _policy(conf):
    return os.getenv("SEND_POLICY", conf.get("send_policy", "permissioned")).strip().lower()


def daily_sent_count(conn, day=None):
    day = day or _today()
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM send_events WHERE status='sent' AND substr(sent_at,1,10)=?",
        (day,),
    ).fetchone()
    return int(row["n"])


def eligible(limit):
    conf = cfg()
    policy = _policy(conf)
    with connect() as c:
        base = """
            SELECT e.id,e.email,c.name,COALESCE(c.sector,'other') sector
            FROM emails e JOIN companies c ON c.id=e.company_id
            LEFT JOIN suppressions s ON lower(s.email)=lower(e.email)
            WHERE e.verified=1
              AND e.status NOT IN ('sent','sending','hard_bounce','suppressed')
              AND s.email IS NULL
              AND e.type!='blocked'
        """
        if policy == "permissioned":
            base += " AND EXISTS (SELECT 1 FROM permissions p WHERE p.email_id=e.id AND p.opted_in=1)"
        elif policy != "permissioned":
            # Non-permissioned sending is intentionally not enabled by this project for Resend.
            raise RuntimeError("Only SEND_POLICY=permissioned is supported by the Resend sender")
        return c.execute(base + " ORDER BY e.score DESC,e.id ASC LIMIT ?", (limit,)).fetchall()


def campaign(limit=40, dry_run=False):
    init_db()
    conf = cfg()
    hard_cap = int(conf["daily_send_limit"])
    limit = min(max(int(limit), 0), hard_cap)
    if limit == 0:
        return []

    campaign_name = "gomaa-radar-daily"
    day = _today()
    results = []
    reply = os.getenv(conf.get("reply_to_env", "REPLY_TO_EMAIL"), "").strip()

    with connect() as c:
        sent_today = daily_sent_count(c, day)
        remaining = max(0, hard_cap - sent_today)
        if remaining == 0:
            return [("", "daily_cap_reached", str(hard_cap))]
        campaign_row = c.execute(
            "SELECT id FROM campaigns WHERE name=? AND campaign_date=? ORDER BY id DESC LIMIT 1",
            (campaign_name, day),
        ).fetchone()
        if campaign_row:
            campaign_id = campaign_row["id"]
        else:
            cur = c.execute(
                "INSERT INTO campaigns(name,campaign_date) VALUES(?,?)",
                (campaign_name, day),
            )
            campaign_id = cur.lastrowid

    rows = eligible(min(limit, remaining))
    for i, row in enumerate(rows):
        subject, body = build(row["name"], row["sector"], "ar")
        if dry_run:
            results.append((row["email"], "dry_run", ""))
            continue

        # Reserve the row before calling the provider. The workflow itself is serialized,
        # and the stable idempotency key in the provider adapter protects provider retries.
        with connect() as c:
            changed = c.execute(
                "UPDATE emails SET status='sending' WHERE id=? AND status NOT IN ('sent','sending','hard_bounce','suppressed')",
                (row["id"],),
            ).rowcount
        if not changed:
            continue

        try:
            data = resend_send(
                row["email"],
                subject,
                body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>"),
                reply or None,
                idempotency_key=f"gomaa-radar-{day}-{row['id']}",
            )
            msg = data.get("id", "")
            with connect() as c:
                c.execute("UPDATE emails SET status='sent',last_checked=CURRENT_TIMESTAMP WHERE id=?", (row["id"],))
                c.execute(
                    "INSERT INTO send_events(email_id,campaign_id,message_id,status,provider_id) VALUES(?,?,?,?,?)",
                    (row["id"], campaign_id, msg, "sent", msg),
                )
            results.append((row["email"], "sent", msg))
        except Exception as e:
            with connect() as c:
                c.execute("UPDATE emails SET status='new' WHERE id=? AND status='sending'", (row["id"],))
                c.execute(
                    "INSERT INTO send_events(email_id,campaign_id,status,error) VALUES(?,?,?,?)",
                    (row["id"], campaign_id, "failed", str(e)[:500]),
                )
            results.append((row["email"], "failed", str(e)[:500]))

        if i < len(rows) - 1:
            time.sleep(int(conf["send_interval_seconds"]))
    return results
