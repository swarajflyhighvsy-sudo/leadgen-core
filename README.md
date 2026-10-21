# leadgen-core

Find local small businesses that could use a simple website or a small automation, rank them by
the gap you can actually see, and keep every first message honest.

Built by Swaraj Yadav in Berlin while looking for his first local clients. The same approach,
applied to an operations team's inbox at iur.crowd as an n8n workflow, reduced manual effort by 85%.

## What it does

1. `neukoelln_list.py`: pulls every named shop, café, salon, practice and trade in a district from
   OpenStreetMap (Overpass), drops chains (anything with a `brand` tag), tags each with a sector,
   the offer that fits it, and the gap OSM shows (no website, no opening hours). Writes a CSV.
2. `guard.py`: a draft guard for first-contact messages. A draft passes only if it ends with a
   question, has no link, no long dash, no pitch word (whole-word match, so "KI" never blocks
   "Kiez"), stays under the limit, and quotes a detail that is really in the source it was
   written from.

Stdlib only. No API keys. No scraping behind logins. Nothing is ever sent by the code.

## Run

```
python3 neukoelln_list.py            # cached after the first Overpass read
python3 neukoelln_list.py --force    # fresh read
python3 guard.py                     # self-check
```

Change the district in the Overpass query at the top of `neukoelln_list.py`
(`Neukölln`, admin_level 9; a whole city is admin_level 4).

## Rules the code keeps

- Every row traces to an OpenStreetMap object you can open (the `osm` column).
- A chain is dropped on the `brand` tag only, so some untagged chains slip through. Check before you knock.
- The guard is a floor, not a writer. It refuses bad drafts; it does not make good ones.

## Licence

MIT.
