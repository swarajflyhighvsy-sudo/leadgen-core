"""
Neukoelln small-business list for local AI, IT and automation offers (life-os.md §4, task 4).

One Overpass read of every named business in Bezirk Neukölln, chains dropped (any brand tag),
each row tagged with a sector, the offer that fits it, and the gap OSM shows (no website, no
hours). Nothing is contacted. Stdlib only; writes a CSV that opens in Numbers or Excel.

    python3 neukoelln_list.py            # uses the cache after the first fetch
    python3 neukoelln_list.py --force    # fresh read from Overpass
"""

import csv
import sys
import time
from pathlib import Path

from sources.osm import fetch_overpass, permalink

QUERY = """
[out:json][timeout:300];
area["name"="Neukölln"]["boundary"="administrative"]["admin_level"="9"]->.b;
(
  nwr["name"]["shop"](area.b);
  nwr["name"]["craft"](area.b);
  nwr["name"]["office"](area.b);
  nwr["name"]["healthcare"](area.b);
  nwr["name"]["amenity"~"^(restaurant|cafe|bar|pub|fast_food|ice_cream|dentist|doctors|clinic|pharmacy|veterinary|driving_school|language_school|music_school|car_wash|car_rental|bicycle_rental|coworking_space|events_venue|nightclub)$"](area.b);
  nwr["name"]["leisure"~"^(fitness_centre|sports_centre|dance)$"](area.b);
  nwr["name"]["tourism"~"^(hotel|guest_house|hostel|apartment)$"](area.b);
);
out center tags;
"""

# sector -> (offer that fits, pain it removes)
SECTORS = {
    "Food & drink": ("Online ordering or table booking, Google profile and review replies, WhatsApp order bot",
                     "phone orders and no-shows"),
    "Beauty & body": ("Online booking with WhatsApp/SMS reminders, review requests after each visit",
                      "no-shows and booking by phone"),
    "Health practice": ("Appointment booking and reminders, digital intake forms, AI phone answering",
                        "phone load at reception"),
    "Retail shop": ("Stock and reorder tracking, online shop or Google listing, offer posts",
                    "stock run-outs and no online presence"),
    "Trades & repair": ("Quote and invoice automation, job scheduling, customer status messages",
                        "paperwork after each job"),
    "Office & services": ("Document intake and data extraction, email triage with draft replies",
                          "manual data entry from mail and PDF"),
    "Fitness & classes": ("Class booking, membership payments and reminders, lead follow-up",
                          "manual sign-ups and churn"),
    "Stay": ("Booking channel sync, automated guest messages and check-in info",
             "double bookings and repeated guest questions"),
    "Other": ("Website, Google profile, one workflow automation", "unknown"),
}

FOOD = {"restaurant", "cafe", "bar", "pub", "fast_food", "ice_cream", "nightclub", "events_venue"}
HEALTH = {"dentist", "doctors", "clinic", "pharmacy", "veterinary"}
BEAUTY_SHOPS = {"hairdresser", "beauty", "cosmetics", "massage", "tattoo", "nail_salon", "perfumery"}
FOOD_SHOPS = {"bakery", "butcher", "pastry", "confectionery", "deli", "coffee", "tea", "wine",
              "beverages", "greengrocer", "seafood", "chocolate"}
REPAIR_SHOPS = {"car_repair", "bicycle", "mobile_phone", "computer", "electronics_repair", "tailor",
                "shoe_repair", "laundry", "dry_cleaning", "locksmith"}
LEARN = {"driving_school", "language_school", "music_school"}


def sector(t: dict) -> str:
    amenity, shop = t.get("amenity", ""), t.get("shop", "")
    if t.get("tourism"):
        return "Stay"
    if amenity in FOOD or shop in FOOD_SHOPS:
        return "Food & drink"
    if t.get("healthcare") == "physiotherapist" or shop in BEAUTY_SHOPS:
        return "Beauty & body"
    if amenity in HEALTH or t.get("healthcare"):
        return "Health practice"
    if t.get("leisure") or amenity in LEARN:
        return "Fitness & classes"
    if t.get("craft") or shop in REPAIR_SHOPS or amenity in {"car_wash", "car_rental", "bicycle_rental"}:
        return "Trades & repair"
    if t.get("office") or amenity == "coworking_space":
        return "Office & services"
    if shop:
        return "Retail shop"
    return "Other"


def row(el: dict) -> dict | None:
    t = el.get("tags") or {}
    # ponytail: "has a brand tag" = chain; misses untagged chains, fine for a first list.
    if any(k.startswith("brand") for k in t) or t.get("operator:type") == "public":
        return None
    sec = sector(t)
    site = t.get("website") or t.get("contact:website") or ""
    phone = t.get("phone") or t.get("contact:phone") or ""
    email = t.get("email") or t.get("contact:email") or ""
    gaps = []
    if not site:
        gaps.append("no website")
    if not t.get("opening_hours"):
        gaps.append("no hours online")
    # A visible gap is the easiest opener; a phone or email makes them reachable.
    score = 2 * (not site) + (not t.get("opening_hours")) + bool(phone) + bool(email)
    kind = t.get("shop") or t.get("amenity") or t.get("craft") or t.get("office") \
        or t.get("healthcare") or t.get("leisure") or t.get("tourism") or ""
    offer = SECTORS[sec][0]
    if not site:
        offer = "Simple website + Google profile first. Then: " + offer
    return {
        "priority": score, "name": t["name"], "sector": sec, "type": kind,
        "street": f"{t.get('addr:street', '')} {t.get('addr:housenumber', '')}".strip(),
        "postcode": t.get("addr:postcode", ""), "phone": phone, "email": email, "website": site,
        "gap": ", ".join(gaps) or "none visible", "offer": offer, "pain": SECTORS[sec][1],
        "osm": permalink(el),
    }


def safe_cell(v) -> str:
    """OSM text goes into a spreadsheet: no long dashes, and no cell that Excel would run as a
    formula (a name starting with =, +, -, @, tab or CR gets a leading apostrophe)."""
    t = str(v).replace("\u2014", "-").replace("\u2013", "-")
    return "'" + t if t[:1] in ("=", "+", "-", "@", "\t", "\r") else t


def main() -> None:
    data = fetch_overpass(QUERY, "osm-neukoelln-smallbiz", force="--force" in sys.argv)
    seen, rows = set(), []
    for el in data.get("elements", []):
        r = row(el)
        key = r and (r["name"].lower(), r["street"].lower())
        if r and key not in seen:
            seen.add(key)
            rows.append(r)
    rows.sort(key=lambda r: (-r["priority"], r["sector"], r["name"].lower()))
    out = Path(__file__).resolve().parent / "out" / f"neukoelln-smallbiz-{time.strftime("%Y-%m-%d")}.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        # OSM names can carry long dashes; nothing handed to Sj may (CLAUDE.md writing rules).
        w.writerows({k: safe_cell(v) for k, v in r.items()} for r in rows)
    print(f"elements {len(data.get('elements', []))}, independent businesses {len(rows)}")
    by = {}
    for r in rows:
        by[r["sector"]] = by.get(r["sector"], 0) + 1
    for s, n in sorted(by.items(), key=lambda x: -x[1]):
        print(f"  {s:<18} {n}")
    print(out)


if __name__ == "__main__":
    # Self-check: chains drop, a cafe with no website gets the website-first offer, formulas are inert.
    assert safe_cell("=1+1") == "'=1+1" and safe_cell("Caf\u00e9 \u2014 Bar") == "Caf\u00e9 - Bar" and safe_cell(5) == "5"
    assert row({"tags": {"name": "X", "shop": "bakery", "brand": "Y"}}) is None
    r = row({"type": "node", "id": 1, "tags": {"name": "Cafe A", "amenity": "cafe", "phone": "1"}})
    assert r["sector"] == "Food & drink" and r["priority"] == 4 and r["offer"].startswith("Simple website")
    main()
