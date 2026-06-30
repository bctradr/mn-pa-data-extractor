"""
9_Admin_Seed_Municipalities.py
ONE-TIME ADMIN TOOL — delete this page after confirming final counts.

Steps performed when Run is clicked:
  1. DELETE all rows WHERE state = 'WI'
  2. DELETE all rows WHERE state IS NULL   (legacy test rows)
  3. Read data/wi_municipalities.csv and insert each row:
       name  → name
       state → 'WI'
       type + county → notes  (e.g. "Town, Marathon County" / "Village" / "City")
       preferred_method, email, fax, portal_url, lead_time_days → NULL
  4. Skip if (name, state) already exists in DB (safe for partial re-runs).
  5. Show final municipality counts by state.
"""

import csv
import os

import pandas as pd
import streamlit as st

from supabase_client import get_supabase
from ui_theme import apply_theme

try:
    st.set_page_config(page_title="Admin: Seed Municipalities", page_icon="🔧", layout="wide")
except Exception:
    pass

apply_theme()

CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "wi_municipalities.csv",
)

BATCH_SIZE = 500


def fetch_all_existing(sb):
    """Paginate past PostgREST's 1000-row default."""
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
    """Paginate to count all rows by state."""
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


def build_notes(row_type: str, county: str) -> str:
    t = (row_type or "").strip().title()
    c = (county or "").strip()
    if t == "Town" and c:
        return f"Town, {c} County"
    return t or None


st.title("🔧 Admin: Seed WI Municipalities")
st.warning(
    "**One-time import from `data/wi_municipalities.csv`.**  "
    "Deletes all existing WI rows and NULL-state rows, then inserts 1,850 WI entries.  "
    "Delete this page after confirming the final counts.",
    icon="⚠️",
)

if not os.path.exists(CSV_PATH):
    st.error(f"CSV not found at `{CSV_PATH}`. Ensure `data/wi_municipalities.csv` is deployed.")
    st.stop()

with open(CSV_PATH, newline="", encoding="utf-8") as f:
    _preview = list(csv.DictReader(f))
st.info(f"CSV ready: **{len(_preview):,} rows** to import.")

if st.button("▶️ Run Import", type="primary"):
    sb = get_supabase()

    with st.status("Running...", expanded=True) as status:

        # 1 — Delete WI rows
        st.write("**Step 1 — DELETE WHERE state = 'WI'**")
        del_wi = sb.table("municipalities").delete().eq("state", "WI").execute()
        st.write(f"  Deleted {len(del_wi.data or []):,} WI rows.")

        # 2 — Delete NULL-state rows
        st.write("**Step 2 — DELETE WHERE state IS NULL**")
        del_null = sb.table("municipalities").delete().is_("state", "null").execute()
        st.write(f"  Deleted {len(del_null.data or []):,} NULL-state rows.")

        # 3 — Read CSV
        st.write("**Step 3 — Read CSV**")
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            csv_rows = list(csv.DictReader(f))
        st.write(f"  {len(csv_rows):,} rows in CSV.")

        # 4 — Dedup check
        st.write("**Step 4 — Check existing DB rows**")
        existing_rows = fetch_all_existing(sb)
        existing = {(r["name"], r.get("state") or "") for r in existing_rows}
        st.write(f"  {len(existing):,} existing rows (MN + any other).")

        to_insert = []
        skipped = 0
        for row in csv_rows:
            name   = (row.get("name") or "").strip()
            state  = (row.get("state") or "WI").strip()
            rtype  = (row.get("type") or "").strip()
            county = (row.get("county") or "").strip()
            if not name:
                continue
            if (name, state) in existing:
                skipped += 1
                continue
            existing.add((name, state))
            notes = build_notes(rtype, county)
            to_insert.append({"name": name, "state": state, "notes": notes})

        st.write(f"  {len(to_insert):,} to insert, {skipped:,} skipped (already exist).")

        # 5 — Batch insert
        st.write(f"**Step 5 — Batch insert ({BATCH_SIZE}/batch)**")
        num_batches = (len(to_insert) + BATCH_SIZE - 1) // BATCH_SIZE if to_insert else 0
        inserted = 0
        errors = 0
        for i in range(0, len(to_insert), BATCH_SIZE):
            batch = to_insert[i : i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            try:
                sb.table("municipalities").insert(batch).execute()
                inserted += len(batch)
                st.write(f"  Batch {batch_num}/{num_batches}: {len(batch)} rows → {inserted} total")
            except Exception as e:
                st.error(f"  Batch {batch_num}/{num_batches} error: {e}")
                errors += len(batch)
        st.write(f"  **{inserted:,} inserted, {errors:,} errors.**")

        # 6 — Final counts
        st.write("**Step 6 — Final counts (paginated)**")
        counts = count_all_by_state(sb)
        status.update(label="Done!", state="complete")

    st.subheader("Final municipality counts by state")
    count_rows = [{"State": s, "Count": c} for s, c in sorted(counts.items())]
    count_rows.append({"State": "TOTAL", "Count": sum(counts.values())})
    st.dataframe(pd.DataFrame(count_rows), hide_index=True, use_container_width=False)

    st.success(
        "✅ Import complete. Confirm the counts above look right, "
        "then I'll delete `pages/9_Admin_Seed_Municipalities.py` and `data/wi_municipalities.csv`."
    )
