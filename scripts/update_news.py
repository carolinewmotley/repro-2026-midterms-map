"""Refresh data/news.json with recent abortion policy headlines for every state.

Runs once a day through GitHub Actions. Uses the free GDELT DOC API, so no key is needed.
"""
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
    "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington State", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}
PER_STATE = 5
PAUSE_SECONDS = 6  # GDELT asks for no more than one request every 5 seconds
OUT = Path(__file__).resolve().parent.parent / "data" / "news.json"
API = "https://api.gdeltproject.org/api/v2/doc/doc"


def term(name):
    return f'"{name}"' if " " in name else name


def fetch(query, limit, timespan="14d"):
    params = urllib.parse.urlencode({
        "query": f"{query} sourcecountry:US sourcelang:english",
        "mode": "artlist", "format": "json", "maxrecords": 40,
        "timespan": timespan, "sort": "datedesc",
    })
    req = urllib.request.Request(f"{API}?{params}", headers={"User-Agent": "abortion-access-map/1.0 (daily refresh)"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        body = resp.read().decode("utf-8", "replace")
    if not body.lstrip().startswith("{"):
        raise RuntimeError(body[:120])
    items, seen = [], set()
    for art in json.loads(body).get("articles", []):
        title = " ".join((art.get("title") or "").split())
        key = title.lower()[:90]
        if not title or key in seen:
            continue
        seen.add(key)
        raw = art.get("seendate", "")
        date = f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}" if len(raw) >= 8 else ""
        items.append({"title": title, "source": art.get("domain", ""), "url": art.get("url", ""), "date": date})
        if len(items) >= limit:
            break
    return items


def main():
    old = {}
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text())
        except Exception:
            old = {}
    data = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "source": "GDELT Project", "national": [], "states": {}}
    try:
        data["national"] = fetch("abortion (law OR ban OR court OR legislature OR ballot)", 8, "3d")
    except Exception as e:
        print("national feed failed:", e)
        data["national"] = old.get("national", [])
    for abbr, name in STATES.items():
        time.sleep(PAUSE_SECONDS)
        try:
            data["states"][abbr] = fetch(f"abortion {term(name)}", PER_STATE)
        except Exception as e:
            print(abbr, "failed:", e)
            data["states"][abbr] = old.get("states", {}).get(abbr, [])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print("wrote", OUT, sum(len(v) for v in data["states"].values()), "state items")


if __name__ == "__main__":
    main()
