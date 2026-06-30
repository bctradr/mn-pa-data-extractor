"""
9_Admin_Seed_Municipalities.py
ONE-TIME ADMIN TOOL — delete this page after seeding is complete.

Diagnostic + seed run. Shows raw Census file counts at every stage before
inserting anything. Fixes the PostgREST 1000-row default cap on both the
existing-check SELECT and the final count SELECT.
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

# "town" intentionally excluded: WI civil towns are distinct entities.
_SUFFIX_RE = re.compile(
    r"\s+(city|village|township|CDP|borough|plantation|grant|location|"
    r"unorganized territory|reservation|community|municipality|"
    r"consolidated government \(balance\)|urban county|"
    r"metro government \(balance\)|metropolitan government \(balance\)|"
    r"charter township|balance)$",
    re.IGNORECASE,
)


def clean_name(raw: str) -> str:
    return _SUFFIX_RE.sub("", raw.strip())


def fetch_all_existing(sb):
    """Paginate past PostgREST's 1000-row default to get all (name, state) pairs."""
    all_rows = []
    page_size = 1000
    page = 0
    while True:
        result = (
            sb.table("municipalities")
            .select("name,state")
            .range(page * page_size, (page + 1) * page_size - 1)
            .execute()
        )
        batch = result.data or []
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
    return all_rows


def count_all_by_state(sb):
    """Paginate to count all rows by state (avoids 1000-row SELECT cap)."""
    counts = {}
    page_size = 1000
    page = 0
    while True:
        result = (
            sb.table("municipalities")
            .select("state")
            .range(page * page_size, (page + 1) * page_size - 1)
            .execute()
        )
        batch = result.data or []
        for r in batch:
            s = r.get("state") or "(none/legacy)"
            counts[s] = counts.get(s, 0) + 1
        if len(batch) < page_size:
            break
        page += 1
    return counts


st.title("🔧 Admin: Seed Municipalities (diagnostic + fix)")
st.warning(
    "**Diagnostic run.** Shows raw Census file counts at every stage, then inserts "
    "only rows not already in DB. Delete this page after seeding is confirmed.",
    icon="⚠️",
)

if st.button("▶️ Run Seed", type="primary"):
    sb = get_supabase()

    with st.status("Running...", expanded=True) as status:

        # ── Step 1: Download ──────────────────────────────────────────────────
        st.write("**Step 1 — Download**")
        req = urllib.request.Request(GAZETTEER_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = resp.read()
        st.write(f"Downloaded {len(data):,} bytes from Census.")

        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            txt_files = [n for n in zf.namelist() if n.lower().endswith(".txt")]
            st.write(f"Files in zip: {zf.namelist()}")
            with zf.open(txt_files[0]) as f:
                content = f.read().decode("latin-1")

        lines = content.splitlines()
        header = [h.strip() for h in lines[0].split("\t")]
        data_lines = lines[1:]

        # ── DIAGNOSTIC 1: raw file row count ─────────────────────────────────
        st.write(f"**Diagnostic 1 — Raw file rows (before any filtering): {len(data_lines):,}**")
        st.write(f"Columns: {header}")

        usps_idx = header.index("USPS")
        name_idx = header.index("NAME")

        # ── DIAGNOSTIC 2: MN+WI rows before suffix strip or dedup ────────────
        raw_mn_wi = [
            l for l in data_lines
            if len(l.split("\t")) > max(usps_idx, name_idx)
            and l.split("\t")[usps_idx].strip() in TARGET_STATES
        ]
        raw_by_state = {}
        for l in raw_mn_wi:
            s = l.split("\t")[usps_idx].strip()
            raw_by_state[s] = raw_by_state.get(s, 0) + 1
        st.write(
            f"**Diagnostic 2 — Rows after state filter (MN+WI), before suffix strip or dedup: "
            f"{len(raw_mn_wi):,}**  "
            + "  |  ".join(f"{s}: {c}" for s, c in sorted(raw_by_state.items()))
        )

        # Sample the first 5 raw WI rows so we can see what the names look like
        wi_samples = [
            l.split("\t")[name_idx].strip()
            for l in raw_mn_wi
            if l.split("\t")[usps_idx].strip() == "WI"
        ][:5]
        st.write(f"First 5 WI raw names: {wi_samples}")

        # ── Step 2: Apply suffix strip + in-file dedup ───────────────────────
        places = []
        seen_in_file = set()
        for line in data_lines:
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
            f"After suffix strip + in-file dedup: {len(places):,} — "
            + "  |  ".join(f"{s}: {c}" for s, c in sorted(by_state.items()))
        )

        # ── Step 3: Check existing (paginated, no 1000-row cap) ──────────────
        st.write("**Step 3 — Checking existing rows in DB (paginated)...**")
        existing_rows = fetch_all_existing(sb)
        st.write(f"**Diagnostic 3 — Rows returned by existing-check SELECT: {len(existing_rows):,}**")
        existing = {(r["name"], r.get("state") or "") for r in existing_rows}

        to_insert = []
        skipped = 0
        for p in places:
            if (p["name"], p["state"]) in existing:
                skipped += 1
            else:
                to_insert.append(p)
                existing.add((p["name"], p["state"]))
        st.write(f"{len(to_insert):,} to insert, {skipped:,} skipped (already exist).")

        # ── Step 4: Batch insert (logs every iteration) ──────────────────────
        st.write(f"**Step 4 — Batch insert ({BATCH_SIZE} per batch)**")
        num_batches = (len(to_insert) + BATCH_SIZE - 1) // BATCH_SIZE if to_insert else 0
        st.write(f"Total batches to run: {num_batches}")

        if not to_insert:
            st.write("Nothing to insert.")
        else:
            inserted = 0
            errors = 0
            for i in range(0, len(to_insert), BATCH_SIZE):
                batch = to_insert[i : i + BATCH_SIZE]
                batch_num = i // BATCH_SIZE + 1
                try:
                    sb.table("municipalities").insert(batch).execute()
                    inserted += len(batch)
                    st.write(f"  Batch {batch_num}/{num_batches}: {len(batch)} rows → {inserted} total inserted")
                except Exception as e:
                    st.error(f"  Batch {batch_num}/{num_batches} error: {e}")
                    errors += len(batch)
            st.write(f"Insert complete: {inserted:,} inserted, {errors:,} errors.")

        # ── Final count (paginated, no 1000-row cap) ─────────────────────────
        st.write("**Final counts — paginated SELECT (no PostgREST cap)...**")
        counts = count_all_by_state(sb)

        status.update(label="Done!", state="complete")

    st.subheader("Municipality counts by state (actual DB totals)")
    import pandas as pd
    count_rows = [{"State": s, "Count": c} for s, c in sorted(counts.items())]
    count_rows.append({"State": "TOTAL", "Count": sum(counts.values())})
    st.dataframe(pd.DataFrame(count_rows), hide_index=True, use_container_width=False)

    st.success(
        "Done! Confirm the counts look right, then delete "
        "`pages/9_Admin_Seed_Municipalities.py` from the repo."
    )
