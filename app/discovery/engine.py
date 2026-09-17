import os, time, yaml, requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from app.storage.db import connect, init_db
from app.extraction.public import extract_many
from app.validation.email import classify, domain_from_url

UA = "GomaaIntelligenceLeadRadar/1.0 (+public-business-discovery)"
TIMEOUT = 20

def load(path):
    with open(path, encoding="utf-8") as f: return yaml.safe_load(f)

def robots_allowed(session, url):
    from urllib.robotparser import RobotFileParser
    p=urlparse(url)
    robots=f"{p.scheme}://{p.netloc}/robots.txt"
    try:
        r=session.get(robots, headers={"User-Agent":UA}, timeout=10)
        if r.status_code in (401,403,429,451): return False
        rp=RobotFileParser(); rp.set_url(robots); rp.parse(r.text.splitlines())
        return rp.can_fetch(UA,url)
    except Exception:
        return False

def polite_get(session, url):
    if not robots_allowed(session,url): return None
    try:
        r=session.get(url, headers={"User-Agent":UA}, timeout=TIMEOUT)
        if r.status_code in (403,429,451): return None
        if r.status_code >= 400: return None
        if "text/html" not in r.headers.get("content-type",""): return None
        return r
    except requests.RequestException:
        return None

def relevant_links(html, base, country, sector):
    soup=BeautifulSoup(html,"html.parser")
    terms=(country+" "+sector).lower().split()
    links=[]
    for a in soup.find_all("a",href=True):
        href=urljoin(base,a["href"])
        text=(a.get_text(" ",strip=True)+" "+href).lower()
        if any(t in text for t in terms if len(t)>2) or any(k in text for k in ("company","business","listing","directory","supplier","category","search","page")):
            if urlparse(href).netloc==urlparse(base).netloc:
                links.append(href)
    return list(dict.fromkeys(links))[:50]

def persist(item, source, source_url, country, sector):
    with connect() as c:
        domain=domain_from_url(item.get("website",""))
        name=item.get("name") or domain or "Unknown business"
        c.execute("""INSERT INTO companies(name,domain,country,sector,website,linkedin,facebook,instagram,whatsapp,source,source_url)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?)
                     ON CONFLICT(domain,name,country) DO UPDATE SET last_seen=CURRENT_TIMESTAMP,source_url=excluded.source_url""",
                  (name,domain,country,sector,item.get("website"),item.get("linkedin"),item.get("facebook"),item.get("instagram"),item.get("whatsapp"),source,source_url))
        row=c.execute("SELECT id FROM companies WHERE name=? AND country=? ORDER BY id DESC LIMIT 1",(name,country)).fetchone()
        if not row: return 0
        cid=row["id"]
        n=0
        for email in item["emails"]:
            role,score=classify(email)
            if role=="blocked": continue
            cur=c.execute("""INSERT OR IGNORE INTO emails(company_id,email,type,score,status,source,source_url,verified)
                             VALUES(?,?,?,?,?,?,?,?)""",(cid,email,role,score,"new",source,source_url,1))
            n += cur.rowcount
        return n

def init_tasks():
    cfg=load("config/sources.yml"); countries=load("config/countries.yml")["countries"]; sectors=load("config/sectors.yml")["sectors"].keys()
    with connect() as c:
        for s in cfg["sources"]:
            for country in countries:
                if country not in s["countries"]: continue
                for sector in sectors:
                    c.execute("INSERT OR IGNORE INTO discovery_tasks(source,country,sector) VALUES(?,?,?)",(s["name"],country,sector))

def discover(limit=120, max_pages=30):
    init_db(); init_tasks()
    sources={x["name"]:x for x in load("config/sources.yml")["sources"]}
    with connect() as c:
        tasks=c.execute("""SELECT * FROM discovery_tasks WHERE status IN ('pending','retry')
                          ORDER BY updated_at LIMIT ?""",(limit,)).fetchall()
    session=requests.Session()
    total=0
    for task in tasks:
        src=sources.get(task["source"])
        if not src: continue
        pages=0; companies=0
        try:
            queue=[src["url"]]; seen=set()
            while queue and pages<max_pages:
                u=queue.pop(0)
                if u in seen: continue
                seen.add(u)
                r=polite_get(session,u)
                if not r: continue
                pages+=1
                items=extract_many(r.text,r.url)
                for item in items:
                    if item["emails"] or item["name"]:
                        companies += persist(item,task["source"],r.url,task["country"],task["sector"])
                queue.extend(relevant_links(r.text,r.url,task["country"],task["sector"]))
                time.sleep(0.7)
            with connect() as c:
                status = 'done' if pages > 0 else 'retry'
                c.execute("""UPDATE discovery_tasks SET status=?,attempts=attempts+1,pages=?,companies=?,updated_at=CURRENT_TIMESTAMP,error=? WHERE id=?""",(status,pages,companies,None if pages > 0 else 'No accessible HTML pages',task["id"]))
            total += companies
        except Exception as e:
            with connect() as c:
                c.execute("""UPDATE discovery_tasks SET status='retry',attempts=attempts+1,error=?,updated_at=CURRENT_TIMESTAMP WHERE id=?""",(str(e)[:500],task["id"]))
    return total
