import csv, json, os
from app.storage.db import connect, init_db

def report():
    init_db()
    with connect() as c:
        rows=c.execute("""SELECT c.name,c.country,c.sector,c.website,e.email,e.type,e.score,e.status,e.source,e.source_url
                          FROM emails e JOIN companies c ON c.id=e.company_id ORDER BY e.score DESC""").fetchall()
    os.makedirs("reports", exist_ok=True)
    Path="reports/leads.csv"
    with open(Path,"w",newline="",encoding="utf-8-sig") as f:
        w=csv.writer(f); w.writerow(rows[0].keys() if rows else ["name"])
        for r in rows: w.writerow(tuple(r))
    with open("reports/leads.json","w",encoding="utf-8") as f:
        json.dump([dict(r) for r in rows],f,ensure_ascii=False,indent=2)
    return len(rows)
