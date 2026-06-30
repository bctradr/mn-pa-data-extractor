#!/usr/bin/env python3
"""
scripts/seed_municipalities.py
One-time seed: bulk-insert MN and WI municipalities from the 2024 Census
Gazetteer Places file (national).

Usage (from project root):
    python scripts/seed_municipalities.py

Credentials: reads SUPABASE_URL + SUPABASE_SERVICE_KEY from
.streamlit/secrets.toml, falling back to environment variables of the same
names. Run supabase/migrations/004_municipalities_state.sql first.
"""

import io
import os
import re
import sys
import zipfile
import urllib.request

GAZETTEER_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "2024_Gazetteer/2024_Gaz_place_national.zip"
)
TARGET_STATES = {"MN", "WI"}
BATCH_SIZE = 500

# Strip legal suffix that Census appends to every place name.
_SUFFIX_RE = re.compile(
    r"\s+(city|village|town|township|CDP|borough|plantation|grant|location|"
    r"unorganized territory|reservation|community|municipality|"
    r"consolidated government \(balance\)|urban county|"
    r"metro government \(balance\)|metropolitan government \(balance\)|"
    r"charter township|balance)$",
    re.IGNORECASE,
)


def clean_name(raw: str) -> str:
    return _SUFFIX_RE.sub("", raw.strip())


def load_credentials():
    """Return (url, service_key) from .streamlit/secrets.toml or env vars."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    toml_path = os.path.join(project_root, ".streamlit", "secrets.toml")

    if os.path.exists(toml_path):
        secrets = {}
        # Try tomllib (Python 3.11+) then tomli, then manual regex extraction.
        try:
            import tomllib
            with open(toml_path, "rb") as f:
                secrets = tomllib.load(f)
        except ImportError:
            try:
                import tomli as tomllib  # pip install tomli
                with open(toml_path, "rb") as f:
                    secrets = tomllib.load(f)
            except ImportError:
                with open(toml_path, "r", encoding="utf-8") as f:
                    content = f.read()
                for key in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY"):
                    m = re.search(rf'{key}\s*=\s*"([^"]+)"', content)
                    if m:
                        secrets[key] = m.group(1)

        url = secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
        key = (
            secrets.get("SUPABASE_SERVICE_KEY")
            or os.environ.get("SUPABASE_SERVICE_KEY")
        )
        if url and key:
            return url, key

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if url and key:
        return url, key

    raise RuntimeError(
        "Supabase credentials not found.\n"
        "Set SUPABASE_URL and SUPABASE_SERVICE_KEY env vars,\n"
        "or ensure .streamlit/secrets.toml exists with those keys."
    )


def download_and_parse():
    print(f"Downloading {GAZETTEER_URL} ...", flush=True)
    req = urllib.request.Request(
        GAZETTEER_URL, headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    print(f"  {len(data):,} bytes received")

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        txt_files = [n for n in zf.namelist() if n.lower().endswith(".txt")]
        if not txt_files:
            raise RuntimeError(f"No .txt file in zip. Contents: {zf.namelist()}")
        filename = txt_files[0]
        print(f"  Parsing {filename} ...")
        with zf.open(filename) as f:
            content = f.read().decode("latin-1")

    lines = content.splitlines()
    header = [h.strip() for h in lines[0].split("\t")]
    print(f"  Columns: {header[:6]} ...")

    try:
        usps_idx = header.index("USPS")
        name_idx = header.index("NAME")
    except ValueError:
        raise RuntimeError(
            f"Expected USPS and NAME columns. Found: {header}"
        )

    places = []
    seen_in_file = set()
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) <= max(usps_idx, name_idx):
            continue
        state = parts[usps_idx].strip()
        if state not in TARGET_STATES:
            continue
        raw_name = parts[name_idx].strip()
        cleaned = clean_name(raw_name)
        if not cleaned:
            continue
        key = (cleaned, state)
        if key in seen_in_file:
            continue  # deduplicate within file (CDP + city same name)
        seen_in_file.add(key)
        places.append({"name": cleaned, "state": state})

    return places


def main():
    url, svc_key = load_credentials()

    from supabase import create_client
    sb = create_client(url, svc_key)
    print("Connected to Supabase.")

    places = download_and_parse()
    by_state = {}
    for p in places:
        by_state[p["state"]] = by_state.get(p["state"], 0) + 1
    print(f"\nPlaces parsed from Census Gazetteer:")
    for state, count in sorted(by_state.items()):
        print(f"  {state}: {count}")
    print(f"  Total: {len(places)}")

    # Fetch existing rows to skip duplicates.
    print("\nFetching existing municipalities ...")
    existing_result = sb.table("municipalities").select("name,state").execute()
    existing = {
        (r["name"], r.get("state") or "")
        for r in (existing_result.data or [])
    }
    print(f"  {len(existing)} already in DB")

    to_insert = []
    skipped = 0
    for p in places:
        if (p["name"], p["state"]) in existing:
            skipped += 1
        else:
            to_insert.append(p)
            existing.add((p["name"], p["state"]))

    print(f"  {len(to_insert)} to insert, {skipped} skipped (already exist)")

    if not to_insert:
        print("\nNothing to insert — all municipalities already in DB.")
    else:
        inserted = 0
        errors = 0
        for i in range(0, len(to_insert), BATCH_SIZE):
            batch = to_insert[i : i + BATCH_SIZE]
            try:
                sb.table("municipalities").insert(batch).execute()
                inserted += len(batch)
                print(
                    f"  Batch {i // BATCH_SIZE + 1}: {inserted}/{len(to_insert)} inserted",
                    flush=True,
                )
            except Exception as e:
                print(
                    f"  ERROR batch {i // BATCH_SIZE + 1}: {e}",
                    file=sys.stderr,
                )
                errors += len(batch)
        print(f"\nInserted {inserted}, errors {errors}")

    # Final count by state
    print("\nFinal municipality counts by state in DB:")
    all_result = sb.table("municipalities").select("state").execute()
    counts = {}
    for r in all_result.data or []:
        s = r.get("state") or "(none/legacy)"
        counts[s] = counts.get(s, 0) + 1
    for state, count in sorted(counts.items()):
        print(f"  {state:20s}: {count:5d}")
    print(f"  {'TOTAL':20s}: {sum(counts.values()):5d}")


if __name__ == "__main__":
    main()
