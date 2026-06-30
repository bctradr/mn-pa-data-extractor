"""
9_Admin_Seed_Municipalities.py
ONE-TIME ADMIN TOOL — delete this page after seeding is complete.

Downloads the 2024 Census Gazetteer national places file, filters to MN/WI,
strips legal suffixes, and batch-inserts all places into the municipalities
table. Safe to re-run: skips rows where (name, state) already exists.
"""

import io
import re
import zipfile
import urllib.request

import streamlit as st
from supabase_client import get_supabase
from ui_theme import apply_theme

try:
    st.set_page_config(page_title="Admin: Seed Municipalities", page_icon="🔧", layout="wide")
except Exception:
    pass

apply_theme()

GAZETTEER_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "2024_Gazetteer/2024_Gaz_place_national.zip"
)
TARGET_STATES = {"MN", "WI"}
BATCH_SIZE = 500

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


st.title("🔧 Admin: Seed Municipalities")
st.warning(
    "**One-time setup tool.** Delete `pages/9_Admin_Seed_Municipalities.py` "
    "after seeding is complete. Safe to re-run — existing rows are skipped.",
    icon="⚠️",
)

if st.button("▶️ Run Seed", type="primary"):
    sb = get_supabase()
    log = st.container()

    with st.status("Seeding municipalities...", expanded=True) as status:

        # 1 — Download
        st.write("Downloading Census Gazetteer national places file (~30 MB)...")
        req = urllib.request.Request(
            GAZETTEER_URL, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = resp.read()
        st.write(f"Downloaded {len(data):,} bytes.")

        # 2 — Parse
        st.write("Parsing and filtering MN/WI places...")
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            txt_files = [n for n in zf.namelist() if n.lower().endswith(".txt")]
            with zf.open(txt_files[0]) as f:
                content = f.read().decode("latin-1")

        lines = content.splitlines()
        header = [h.strip() for h in lines[0].split("\t")]
        usps_idx = header.index("USPS")
        name_idx = header.index("NAME")

        places = []
        seen_in_file = set()
        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) <= max(usps_idx, name_idx):
                continue
            state = parts[usps_idx].strip()
            if state not in TARGET_STATES:
                continue
            cleaned = clean_name(parts[name_idx].strip())
            if not cleaned:
                continue
            key = (cleaned, state)
            if key in seen_in_file:
                continue
            seen_in_file.add(key)
            places.append({"name": cleaned, "state": state})

        by_state = {}
        for p in places:
            by_state[p["state"]] = by_state.get(p["state"], 0) + 1
        st.write(
            f"Parsed: "
            + ", ".join(f"{s}={c}" for s, c in sorted(by_state.items()))
            + f" (total {len(places)})"
        )

        # 3 — Check existing
        st.write("Checking existing municipalities in DB...")
        existing_result = sb.table("municipalities").select("name,state").execute()
        existing = {
            (r["name"], r.get("state") or "")
            for r in (existing_result.data or [])
        }
        st.write(f"{len(existing)} municipalities already in DB.")

        to_insert = []
        skipped = 0
        for p in places:
            if (p["name"], p["state"]) in existing:
                skipped += 1
            else:
                to_insert.append(p)
                existing.add((p["name"], p["state"]))
        st.write(f"{len(to_insert)} to insert, {skipped} skipped.")

        # 4 — Batch insert
        if not to_insert:
            st.write("Nothing to insert.")
        else:
            inserted = 0
            errors = 0
            for i in range(0, len(to_insert), BATCH_SIZE):
                batch = to_insert[i : i + BATCH_SIZE]
                try:
                    sb.table("municipalities").insert(batch).execute()
                    inserted += len(batch)
                    st.write(
                        f"Batch {i // BATCH_SIZE + 1}: {inserted}/{len(to_insert)} inserted"
                    )
                except Exception as e:
                    st.error(f"Batch {i // BATCH_SIZE + 1} error: {e}")
                    errors += len(batch)
            st.write(f"Inserted {inserted}, errors {errors}.")

        # 5 — Final counts
        st.write("Fetching final counts...")
        all_result = sb.table("municipalities").select("state").execute()
        counts = {}
        for r in all_result.data or []:
            s = r.get("state") or "(none/legacy)"
            counts[s] = counts.get(s, 0) + 1

        status.update(label="Seeding complete!", state="complete")

    st.subheader("Municipality counts by state")
    count_rows = [
        {"State": s, "Count": c} for s, c in sorted(counts.items())
    ]
    count_rows.append({"State": "TOTAL", "Count": sum(counts.values())})
    import pandas as pd
    st.dataframe(pd.DataFrame(count_rows), hide_index=True, use_container_width=False)

    st.success(
        "Done! You can now delete `pages/9_Admin_Seed_Municipalities.py` "
        "from the repo."
    )
