import argparse
from app.storage.db import init_db
from app.discovery.engine import discover
from app.sending.engine import campaign
from app.report import report

p=argparse.ArgumentParser()
sub=p.add_subparsers(dest="cmd",required=True)
sub.add_parser("init-db")
d=sub.add_parser("discover"); d.add_argument("--limit",type=int,default=120); d.add_argument("--max-pages",type=int,default=30)
c=sub.add_parser("campaign"); c.add_argument("--limit",type=int,default=40); c.add_argument("--dry-run",action="store_true")
sub.add_parser("report")
sub.add_parser("maintenance")
a=p.parse_args()

if a.cmd=="init-db": init_db(); print("DB initialized")
elif a.cmd=="discover": print(f"Discovered/processed emails: {discover(a.limit,a.max_pages)}")
elif a.cmd=="campaign":
    results=campaign(a.limit,a.dry_run)
    print(f"Campaign processed: {len(results)}")
    for r in results: print(r)
elif a.cmd=="report": print(f"Lead rows: {report()}")
elif a.cmd=="maintenance":
    from app.maintenance import run
    run()
