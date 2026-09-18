import argparse
import os
from app.storage.db import init_db
from app.discovery.engine import discover
from app.sending.engine import campaign
from app.report import report

def positive_int_env(name, default):
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default

p=argparse.ArgumentParser()
sub=p.add_subparsers(dest="cmd",required=True)
sub.add_parser("init-db")
d=sub.add_parser("discover"); d.add_argument("--limit",type=int,default=positive_int_env("DISCOVERY_TASK_LIMIT", 60)); d.add_argument("--max-pages",type=int,default=positive_int_env("DISCOVERY_MAX_PAGES", 12)); d.add_argument("--max-runtime-seconds",type=int,default=positive_int_env("DISCOVERY_MAX_RUNTIME_SECONDS", 2400))
c=sub.add_parser("campaign"); c.add_argument("--limit",type=int,default=40); c.add_argument("--dry-run",action="store_true")
sub.add_parser("report")
sub.add_parser("maintenance")
a=p.parse_args()

if a.cmd=="init-db": init_db(); print("DB initialized")
elif a.cmd=="discover": print(f"Discovered/processed emails: {discover(a.limit,a.max_pages,a.max_runtime_seconds)}")
elif a.cmd=="campaign":
    results=campaign(a.limit,a.dry_run)
    print(f"Campaign processed: {len(results)}")
    for r in results: print(r)
elif a.cmd=="report": print(f"Lead rows: {report()}")
elif a.cmd=="maintenance":
    from app.maintenance import run
    run()
