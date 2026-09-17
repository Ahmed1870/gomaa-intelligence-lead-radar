import yaml

def mapping():
    with open("config/service_mapping.yml",encoding="utf-8") as f:
        return yaml.safe_load(f)["services"]

def match(sector):
    data=mapping()
    hits=[]
    for key,meta in data.items():
        if sector in meta.get("sectors",[]) or "other" in meta.get("sectors",[]) and not hits:
            hits.append((key,meta))
    if not hits:
        hits=list(data.items())[:2]
    return hits[:3]
