"""Publish weekly pollen LEVELS for every UCT sampling site to data/pollen.json.

For app users without their own data repo. Only the derived levels (low /
moderate / high per category), the dominant tree, dates and a link back to each
UCT report are published; the reports' own text stays on pollencount.co.za.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_pollen as fp

PATH = os.path.join("data", "pollen.json")
KEEP = ("tree", "grass", "weed", "mould", "dominant", "estimated")

def strip(row):
    return {"date": row["date"], "periodStart": row["periodStart"], "periodEnd": row["periodEnd"], "link": row["link"],
            "sites": {n: {k: v.get(k) for k in KEEP} for n, v in row["sites"].items()}}

def main():
    first = not os.path.exists(PATH)
    try:
        feed = fp.fetch(100 if first else 10)
    except Exception as e:
        print("pollen: could not reach pollencount.co.za:", e); return 1
    if feed and all(len(fp.sections(r["content"]["rendered"])) < 2 for r in feed[:3]):
        print("pollen: no site sections found in the latest reports; the format may have changed."); return 1
    store = {} if first else json.load(open(PATH))
    reports = store.get("reports", {})
    before = json.dumps(reports, sort_keys=True)
    for r in feed:
        row = fp.build(r)
        reports[row["date"]] = strip(row)
    store = {"format": "moonlit-sinus-pollen-levels/1",
             "source": "Levels read from the UCT Lung Institute weekly pollen reports. Full reports: https://pollencount.co.za/report/",
             "sites": {k: {"lat": v[0], "lon": v[1]} for k, v in fp.SITE_COORDS.items()},
             "reports": dict(sorted(reports.items()))}
    if json.dumps(store["reports"], sort_keys=True) == before and not first:
        print("pollen: nothing new"); return 0
    os.makedirs("data", exist_ok=True)
    with open(PATH, "w") as f:
        json.dump(store, f, indent=1, ensure_ascii=False); f.write("\n")
    print("pollen: updated", len(store["reports"]), "reports")
    return 0

if __name__ == "__main__":
    sys.exit(main())
