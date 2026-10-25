"""Add weekly pollen levels for every UCT sampling site to pollen.json.

Source: https://pollencount.co.za (UCT Lung Institute Allergy & Immunology Unit).
The site's public WordPress feed is read once a day; only reports not already
stored (or edited since) are added. Reports are written as sentences ("Tree pollen
was moderate to high ..."), so levels for trees, grass, weeds and moulds are read
from each site's paragraph. The raw paragraph is kept so levels can be checked.
Sites that weren't sampled that week ("would be low", "mean counts from previous
years") are marked estimated.

Exit codes: 0 ok, 1 fetch failed or the report format has changed.
"""
import html, json, re, sys, time, urllib.request, datetime

FEED = ("https://pollencount.co.za/wp-json/wp/v2/report?per_page={n}"
        "&_fields=id,date,modified,link,title,content")
UA = "Mozilla/5.0 (Moonlit Sinus Log personal tracker; weekly read; contact kobusprinsloo@gmail.com)"
LEVELS = ["very low", "low", "moderate", "high", "very high"]
CATS = {
    "tree":  r"\btrees?\b",
    "grass": r"\bgrass(?:es)?\b",
    "weed":  r"\bweeds?\b",
    "mould": r"\bmou?lds?\b|\bfungal spores?\b",
}
LEVEL_RE = re.compile(r"\b(extremely low|very low|very high|extremely high|low|moderate|high|significant|elevated)\b", re.I)
NORMAL = {"extremely low": "very low", "extremely high": "very high", "significant": "high", "elevated": "high"}
NOISE = re.compile(r"\blow(er)? temperatures?\b|\bhigh(er)? temperatures?\b|\bhigh(er)? humidity\b|\bhigh winds?\b", re.I)

def fetch(n):
    req = urllib.request.Request(FEED.format(n=n), headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 3: raise
            time.sleep(5 * (attempt + 1))

# Sampling sites (approximate trap locations) and the heading spellings used in reports.
SITE_COORDS = {
    "Cape Town": (-33.95, 18.47), "Johannesburg": (-26.19, 28.03), "Johannesburg South": (-26.27, 27.95),
    "Pretoria": (-25.75, 28.23), "Bloemfontein": (-29.11, 26.19), "Kimberley": (-28.74, 24.77),
    "Durban": (-29.86, 31.02), "Gqeberha": (-33.96, 25.60), "George": (-33.96, 22.46),
    "Potchefstroom": (-26.69, 27.09), "Vanderbijlpark": (-26.71, 27.84), "East London": (-33.02, 27.91),
    "Polokwane": (-23.90, 29.45), "Mbombela": (-25.47, 30.97), "Stellenbosch": (-33.93, 18.86),
}
ALIASES = {"kimberly": "Kimberley", "port elizabeth": "Gqeberha", "tshwane": "Pretoria", "nelspruit": "Mbombela",
           "vandebijlpark": "Vanderbijlpark", "south of johannesburg (vanderbijlpark)": "Vanderbijlpark",
           "johannesburg central": "Johannesburg"}
STOP_HEADINGS = re.compile(r"^(summary|reference range|unit\b|grass:|trees:|weeds:|moulds:|key\b)", re.I)

def lines(rendered):
    t = re.sub(r"<br\s*/?>|</p>|</h\d>|</li>|</div>", "\n", rendered, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", "", t)).replace("\xa0", " ")
    return [re.sub(r"\s+", " ", l).strip() for l in t.split("\n") if l.strip()]

def site_name(line):
    """Canonical site name if this line is a site heading, else None."""
    if len(line) > 45 or "." in line: return None
    key = line.strip().rstrip(":").strip().lower()
    if key in ALIASES: return ALIASES[key]
    for name in SITE_COORDS:
        if key == name.lower(): return name
    return None

def sections(rendered):
    out, cur, buf = {}, None, []
    def flush():
        if cur and buf: out[cur] = " ".join(buf).strip()
    for line in lines(rendered):
        name = site_name(line)
        if name or STOP_HEADINGS.match(line):
            flush(); cur, buf = name, []
            continue
        if cur: buf.append(line)
    flush()
    return out

def cape_town_text(rendered):
    return sections(rendered).get("Cape Town")

ESTIMATE = re.compile(r"\bwould be\b|\bmight include\b|\bmean counts? from previous years\b|\b\d-year means?\b|\bfindings for \d{4} are shown\b|\bnot (?:been )?sampled\b", re.I)

POLLEN_ALL = r"\b(?:all (?:the )?)?pollen\b"

def levels_from(text):
    """Highest level stated for each category in the Cape Town paragraph.
    A sentence about 'pollen' in general sets trees, grass and weeds."""
    found = {}
    def put(c, lv):
        if c not in found or LEVELS.index(lv) > LEVELS.index(found[c]): found[c] = lv
    for s in re.split(r"(?<=[.;])\s+", text):
        s = NOISE.sub(" ", s)
        carry = []
        for seg in re.split(r"\b(?:while|but|whereas|although|however)\b", s, flags=re.I):
            cats = [c for c, rx in CATS.items() if re.search(rx, seg, re.I)]
            own = bool(cats)
            if not cats and re.search(POLLEN_ALL, seg, re.I): cats, own = ["tree", "grass", "weed"], True
            elif re.search(POLLEN_ALL + r"\s+and\s+(?:mou?lds?|fungal)", seg, re.I): cats = sorted(set(cats) | {"tree", "grass", "weed"})
            words = [w.lower() for w in LEVEL_RE.findall(seg)]
            if not own: words = [w for w in words if w != "significant"]
            lv = [NORMAL.get(w, w) for w in words]
            if not cats: cats = carry
            if cats and lv:
                top = max(lv, key=LEVELS.index)
                for c in cats: put(c, top)
            if cats: carry = cats
    return found

def dominant(text):
    m = re.search(r"dominant tree\s+(?:was\s+|is\s+)?([a-z][a-z \-']{1,30}?)\s*\(", text, re.I)
    return m.group(1).strip().lower() if m else None

STOP = re.compile(r"(?:\b(?:and|the|for|are|is|was|include[sd]?|including|detected|dominant|types?|trees?|weeds?|grass(?:es)?|"
                  r"concentrations?|other|seen|peaks?|of)\s+|were\s+)", re.I)

def plants(text):
    """Common names listed before a Latin name in brackets, e.g. 'olive (Oleaceae)'."""
    names = []
    for m in re.finditer(r"([A-Za-z][A-Za-z '\-]{1,60}?)\s*\(([A-Z][A-Za-z\-]+(?:-type)?)\)", text):
        n = m.group(1).strip()
        parts = STOP.split(n)
        n = parts[-1].strip().lower() if parts else n.lower()
        n = " ".join(n.split()[-3:])
        if n and len(n) > 2 and n not in names: names.append(n)
    return names

def report_date(r):
    """The title date ('23 October 2026'), unless it is clearly a typo, then the publish date."""
    pub = datetime.date.fromisoformat(r["date"][:10])
    t = html.unescape(r["title"]["rendered"]).strip()
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            d = datetime.datetime.strptime(t, fmt).date()
            if abs((d - pub).days) <= 10: return d.isoformat()
        except ValueError: pass
    return pub.isoformat()

def site_row(text):
    lv = levels_from(text)
    return {"tree": lv.get("tree"), "grass": lv.get("grass"), "weed": lv.get("weed"), "mould": lv.get("mould"),
            "dominant": dominant(text), "plants": plants(text), "estimated": bool(ESTIMATE.search(text)), "text": text}

def build(r):
    d = report_date(r)
    secs = sections(r["content"]["rendered"])
    start = (datetime.date.fromisoformat(d) - datetime.timedelta(days=6)).isoformat()
    row = {"date": d, "periodStart": start, "periodEnd": d, "link": r["link"], "source": "UCT Lung Institute (pollencount.co.za)",
           "published": r["date"], "sites": {name: site_row(t) for name, t in sorted(secs.items())}}
    ct = row["sites"].get("Cape Town")          # kept at the top level for older app versions
    row["capeTown"] = ct["text"] if ct else None
    if ct: row.update({k: ct[k] for k in ("tree", "grass", "weed", "mould", "dominant", "plants")})
    return row

def main(backfill=False):
    try:
        feed = fetch(100 if backfill else 10)
    except Exception as e:
        print("pollen: could not reach pollencount.co.za:", e); return 1
    store = json.load(open("pollen.json")) if not backfill else {}
    store.setdefault("format", "moonlit-sinus-pollen/1")
    store["note"] = "Weekly counts for each UCT sampling site. Each report is applied to the 7 days ending on its date."
    store["sites"] = {k: {"lat": v[0], "lon": v[1]} for k, v in SITE_COORDS.items()}
    reports = store.setdefault("reports", {})
    added = []
    for r in feed:
        row = build(r)
        prev = reports.get(row["date"])
        if prev and prev.get("published") == row["published"] and prev.get("modifiedSeen") == r.get("modified") and "sites" in prev: continue
        row["modifiedSeen"] = r.get("modified")
        reports[row["date"]] = row; added.append(row["date"])
    recent = feed[:3]
    if recent and all(len(sections(r["content"]["rendered"])) < 2 for r in recent):
        print("pollen: no site sections found in the last 3 reports; the report format may have changed."); return 1
    store["reports"] = dict(sorted(reports.items()))
    with open("pollen.json", "w") as f:
        json.dump(store, f, indent=1, ensure_ascii=False); f.write("\n")
    print("pollen added: " + (", ".join(sorted(added)) if added else "nothing new"))
    return 0

if __name__ == "__main__":
    sys.exit(main(backfill="--backfill" in sys.argv))
