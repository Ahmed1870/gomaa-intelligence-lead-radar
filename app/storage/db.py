import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", "data/jobs.db"))
SCHEMA_VERSION = 2


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS companies(
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          domain TEXT,
          country TEXT,
          city TEXT,
          sector TEXT,
          website TEXT,
          linkedin TEXT,
          facebook TEXT,
          instagram TEXT,
          whatsapp TEXT,
          source TEXT,
          source_url TEXT,
          first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
          last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(domain,name,country)
        );
        CREATE TABLE IF NOT EXISTS emails(
          id INTEGER PRIMARY KEY,
          company_id INTEGER NOT NULL,
          email TEXT NOT NULL UNIQUE,
          type TEXT,
          score INTEGER DEFAULT 0,
          status TEXT DEFAULT 'new',
          source TEXT,
          source_url TEXT,
          verified INTEGER DEFAULT 0,
          validation_status TEXT DEFAULT 'syntax_valid',
          last_checked TEXT,
          FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS permissions(
          email_id INTEGER PRIMARY KEY,
          opted_in INTEGER NOT NULL DEFAULT 0,
          evidence TEXT,
          recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(email_id) REFERENCES emails(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS suppressions(
          email TEXT PRIMARY KEY,
          reason TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS campaigns(
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          campaign_date TEXT NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS send_events(
          id INTEGER PRIMARY KEY,
          email_id INTEGER NOT NULL,
          campaign_id INTEGER NOT NULL,
          message_id TEXT,
          sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
          status TEXT NOT NULL,
          provider_id TEXT,
          error TEXT,
          FOREIGN KEY(email_id) REFERENCES emails(id) ON DELETE CASCADE,
          FOREIGN KEY(campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_send_events_sent_at ON send_events(sent_at);
        CREATE INDEX IF NOT EXISTS idx_send_events_status ON send_events(status);
        CREATE INDEX IF NOT EXISTS idx_emails_status_score ON emails(status, score DESC);
        CREATE INDEX IF NOT EXISTS idx_suppressions_email ON suppressions(email);
        CREATE TABLE IF NOT EXISTS discovery_tasks(
          id INTEGER PRIMARY KEY,
          source TEXT,
          country TEXT,
          sector TEXT,
          status TEXT DEFAULT 'pending',
          attempts INTEGER DEFAULT 0,
          pages INTEGER DEFAULT 0,
          companies INTEGER DEFAULT 0,
          error TEXT,
          updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(source,country,sector)
        );
        CREATE INDEX IF NOT EXISTS idx_discovery_tasks_status ON discovery_tasks(status, updated_at);
        """)

        # Lightweight migrations for databases created by older project versions.
        cols = {r[1] for r in c.execute("PRAGMA table_info(emails)").fetchall()}
        if "validation_status" not in cols:
            c.execute("ALTER TABLE emails ADD COLUMN validation_status TEXT DEFAULT 'syntax_valid'")
        campaign_cols = {r[1] for r in c.execute("PRAGMA table_info(campaigns)").fetchall()}
        if "campaign_date" not in campaign_cols:
            c.execute("ALTER TABLE campaigns ADD COLUMN campaign_date TEXT")
            c.execute("UPDATE campaigns SET campaign_date=substr(created_at,1,10) WHERE campaign_date IS NULL")
        c.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
