"""
OpenStreetMap source: every named business in a district, with a stable object id.

Why OSM and not a language model: a model asked to name companies will produce plausible
names, some of which do not exist, and nothing downstream can tell the difference. OSM rows are real surveyed places, each with
a stable object id that a reader can open and check.


Stdlib only, on purpose. No packages are installed for this project.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"

# Every value in this system has to trace to a page a reader can open.
# For an OSM node/way/relation that page is the object's own permalink.
OSM_PERMALINK = "https://www.openstreetmap.org/{kind}/{oid}"

# Office query: businesses whose daily work is document and data heavy.
# Only used when the job-post source runs short, and every row says it has no trigger.
QUERY_OFFICES_BERLIN = """
[out:json][timeout:300];
area["name"="Berlin"]["boundary"="administrative"]["admin_level"="4"]->.b;
nwr["office"~"^(logistics|accountant|tax_advisor|insurance|estate_agent|company)$"]["website"](area.b);
out center tags;
"""


def _cache_path(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / name


def fetch_overpass(query: str, cache_name: str, force: bool = False) -> dict:
    """
    Fetch and cache. The cache is not an optimisation: every row has to trace back to bytes
    that were actually read, so the raw response is kept with the time it was read.
    """
    raw_path = _cache_path(cache_name + ".json")
    meta_path = _cache_path(cache_name + ".meta.json")

    if raw_path.exists() and not force:
        return json.loads(raw_path.read_text(encoding="utf-8"))

    body = urllib.parse.urlencode({"data": query}).encode("utf-8")
    last_error = None

    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    endpoint,
                    data=body,
                    headers={
                        "User-Agent": "leadgen/0.1 (research)",
                        "Accept": "application/json",
                    },
                )
                with urllib.request.urlopen(req, timeout=300) as resp:
                    payload = resp.read().decode("utf-8")
                data = json.loads(payload)
                raw_path.write_text(payload, encoding="utf-8")
                meta_path.write_text(
                    json.dumps(
                        {
                            "endpoint": endpoint,
                            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            "query": query.strip(),
                            "element_count": len(data.get("elements", [])),
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                return data
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
                last_error = exc
                time.sleep(5 * (attempt + 1))

    raise RuntimeError(f"Overpass unreachable on all endpoints: {last_error!r}")


def permalink(element: dict) -> str:
    kind = element.get("type", "node")
    return OSM_PERMALINK.format(kind=kind, oid=element.get("id"))


def offices_berlin(force: bool = False) -> list[dict]:
    """Raw OSM elements for the office query above. Filtering happens in the caller."""
    data = fetch_overpass(QUERY_OFFICES_BERLIN, "osm-offices-berlin", force=force)
    return data.get("elements", [])


if __name__ == "__main__":
    els = offices_berlin()
    named = [e for e in els if (e.get("tags") or {}).get("name")]
    with_site = [e for e in named if (e.get("tags") or {}).get("website") or (e.get("tags") or {}).get("contact:website")]
    with_phone = [e for e in named if (e.get("tags") or {}).get("phone") or (e.get("tags") or {}).get("contact:phone")]
    print(f"elements returned : {len(els)}")
    print(f"with a name tag   : {len(named)}")
    print(f"  ... with website: {len(with_site)}")
    print(f"  ... with phone  : {len(with_phone)}")
