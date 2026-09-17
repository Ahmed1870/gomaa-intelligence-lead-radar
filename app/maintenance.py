from datetime import datetime, timezone, timedelta
from app.storage.db import connect, init_db


def run():
    init_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(timespec="seconds")
    with connect() as c:
        # Recover rows left in 'sending' if a runner died before updating them.
        c.execute(
            "UPDATE emails SET status='new' WHERE status='sending' AND last_checked IS NOT NULL AND last_checked < ?",
            (cutoff,),
        )
        # A fresh database uses NULL last_checked, so recover any stale sending row conservatively
        # when its most recent event is older than two days.
        c.execute("""
            UPDATE emails SET status='new'
            WHERE status='sending' AND id IN (
              SELECT e.id FROM emails e
              LEFT JOIN send_events se ON se.email_id=e.id
              GROUP BY e.id
              HAVING MAX(se.sent_at) IS NULL OR MAX(se.sent_at) < ?
            )
        """, (cutoff,))
    print("Maintenance completed")
