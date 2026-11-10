"""Refresh data/news.json with recent abortion policy headlines, nationally and for each state.

Runs once a day through GitHub Actions and uses the free GDELT DOC API, so no key is needed.

GDELT rate-limits shared cloud addresses, so the script makes only a few broad requests,
retries with backoff when it is told to slow down, and sorts the results into states by the
state name in each headline. Headlines must be about abortion or reproductive health to be kept.
State lists build up across runs, so a quiet day does not empty the map.
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
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
QUERIES = [
    "abortion",
    '(mifepristone OR "abortion pill" OR "reproductive rights" OR "Planned Parenthood" OR "reproductive health")',
]
TIMESPAN = "7d"
PER_STATE = 5
NATIONAL = 8
STATE_DAYS = 45      # how long a state headline stays in the feed
NATIONAL_DAYS = 7    # the page labels the national list "This week"
PAUSE_SECONDS = 10
RETRY_WAITS = [30, 60, 120, 240]
OUT = Path(__file__).resolve().parent.parent / "data" / "news.json"
API = "https://api.gdeltproject.org/api/v2/doc/doc"

TOPIC = re.compile(
    r"\babortion|\breproductive\b|mifepristone|misoprostol|planned parenthood|\broe\b|\bdobbs\b|"
    r"\bivf\b|in vitro|contracepti|birth control|miscarr|pregnan|\bemtala\b|personhood",
    re.I,
)
# Phrases that contain a state name but are not about that state.
NOT_STATES = re.compile(r"new york times|new york post|washington post|washington examiner|west virginia", re.I)
STATE_PATTERNS = {
    abbr: re.compile(r"\b" + re.escape(name) + r"\b", re.I)
    for abbr, name in STATES.items() if abbr not in ("WA", "WV")
}
STATE_PATTERNS["WA"] = re.compile(r"\bwashington state\b", re.I)
STATE_PATTERNS["WV"] = re.compile(r"\bwest virginia\b", re.I)


def log(*args):
    print(*args, flush=True)


def clean(title):
    t = " ".join((title or "").split())
    t = re.sub(r"\s+'\s*(s|t|re|ve|ll|d)\b", r"'\1", t)   # GDELT writes "Trump ' s"
    t = re.sub(r"\s+([,.;:!?%)\]])", r"\1", t)
    t = re.sub(r"([(\[])\s+", r"\1", t)
    return t


def key(item):
    return re.sub(r"[^a-z0-9]", "", item.get("title", "").lower())[:80]


def fetch(query):
    params = urllib.parse.urlencode({
        "query": f"{query} sourcecountry:US sourcelang:english",
        "mode": "artlist", "format": "json", "maxrecords": 250,
        "timespan": TIMESPAN, "sort": "datedesc",
    })
    req = urllib.request.Request(f"{API}?{params}", headers={"User-Agent": "abortion-access-map/1.1 (daily refresh)"})
    for attempt, wait in enumerate([0] + RETRY_WAITS):
        if wait:
            log(f"  waiting {wait}s before retry {attempt}")
            time.sleep(wait)
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                body = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            log(f"  HTTP {e.code}")
            if e.code in (429, 500, 502, 503, 504):
                continue
            raise
        except Exception as e:  # timeouts and connection resets
            log(f"  {type(e).__name__}: {e}")
            continue
        if not body.lstrip().startswith("{"):
            log("  non-JSON reply:", body[:100].replace("\n", " "))
            continue
        items = []
        for art in json.loads(body).get("articles", []):
            title = clean(art.get("title"))
            raw = art.get("seendate", "")
            date = f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}" if len(raw) >= 8 else ""
            if title and art.get("url"):
                items.append({"title": title, "source": art.get("domain", ""), "url": art["url"], "date": date})
        return items
    raise RuntimeError("gave up after retries")


def on_topic(item):
    return bool(TOPIC.search(item.get("title", "")))


def states_in(item):
    title = item.get("title", "")
    found = [abbr for abbr, pat in STATE_PATTERNS.items() if pat.search(NOT_STATES.sub(" ", title))]
    if STATE_PATTERNS["WV"].search(title):
        found.append("WV")
    return found


def merge(new, old, since, limit, state=None):
    out, seen = [], set()
    for item in sorted(new + old, key=lambda i: i.get("date", ""), reverse=True):
        k = key(item)
        if not k or k in seen or item.get("date", "") < since or not on_topic(item):
            continue
        if state and state not in states_in(item):
            continue
        seen.add(k)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def main():
    old = {}
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text())
        except Exception:
            old = {}
    now = datetime.now(timezone.utc)

    found, ok = [], False
    for i, q in enumerate(QUERIES):
        if i:
            time.sleep(PAUSE_SECONDS)
        log("query:", q)
        try:
            items = fetch(q)
            ok = True
            log(f"  {len(items)} articles")
            found.extend(items)
        except Exception as e:
            log("  failed:", e)

    relevant = [i for i in found if on_topic(i)]
    log(f"{len(relevant)} of {len(found)} headlines are on topic")

    state_since = (now - timedelta(days=STATE_DAYS)).strftime("%Y-%m-%d")
    nat_since = (now - timedelta(days=NATIONAL_DAYS)).strftime("%Y-%m-%d")
    by_state = {abbr: [] for abbr in STATES}
    for item in relevant:
        for abbr in states_in(item):
            by_state[abbr].append(item)

    old_states = old.get("states", {})
    data = {
        "updated": now.strftime("%Y-%m-%dT%H:%M:%SZ") if ok else old.get("updated"),
        "source": "GDELT Project",
        "national": merge(relevant, old.get("national", []), nat_since, NATIONAL),
        "states": {abbr: merge(by_state[abbr], old_states.get(abbr, []), state_since, PER_STATE, abbr) for abbr in STATES},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    filled = sum(1 for v in data["states"].values() if v)
    log(f"wrote {OUT}: {len(data['national'])} national, {filled} states with headlines")


if __name__ == "__main__":
    main()
