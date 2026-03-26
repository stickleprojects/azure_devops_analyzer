"""Audit dashboard JSON files and report SQL targets using views vs raw SQL."""
import json
import glob
import re


def walk_panels(panels):
    for p in panels:
        yield p
        yield from walk_panels(p.get("panels", []))


total = 0
views = 0
raw = []

for f in sorted(glob.glob("dashboards/*.json")):
    data = json.load(open(f))
    fname = f.split("/")[-1].split("\\")[-1]
    for p in walk_panels(data.get("panels", [])):
        for t in p.get("targets", []):
            sql = t.get("rawSql", "")
            if not sql:
                continue
            total += 1
            if re.search(r"FROM\s+v_\w+", sql, re.IGNORECASE):
                views += 1
            else:
                raw.append((fname, p.get("id"), p.get("title", "?"), sql[:80]))

print(f"Total SQL targets : {total}")
print(f"Using views       : {views}")
print(f"Still raw SQL     : {len(raw)}")
if raw:
    print()
    for fname, pid, title, sql in raw:
        print(f"  [{fname}] panel {pid} \"{title}\"")
        print(f"    {sql!r}")
