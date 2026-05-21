# Repo Issues — Review Findings

Snapshot of inconsistencies and fragile spots identified during a repo walkthrough.
Documented only — no fixes applied yet.

---

## Fix soon

These either silently corrupt output, block users, or actively mislead.

### 1. Published CSV silently drops fields
`pages/3_PA_Extractor.py:158` defines a rich `flatten_for_csv` (unit_no, full
financing breakdown, well/septic, HOA, home warranty, FIRPTA, other_terms).
`extractor.py:81` defines an older, slimmer version. Standalone export uses
the rich one; review-mode **Publish CSV** uses `flatten_combined_for_csv`
which calls the slim one. v2 also imports the slim one. Result: CSVs going to
TPS via the queue are missing fields that the standalone export includes.
Same data, different output — silent data loss.

### 2. Uploader accepts non-PDFs but extractor only handles PDFs
`pages/1_New_Order.py:65` accepts `pdf, docx, msg, eml`. `extractor.extract_from_pdf`
base64-encodes the bytes and hard-codes `media_type: application/pdf`. The
moment a user uploads a `.docx` / `.msg` / `.eml` and someone hits Extract from
the queue, the call will either fail or feed Claude garbage that looks like a
PDF. Either narrow the uploader to PDF-only, or route non-PDF bytes around the
extractor.

### 3. README and DEPLOYMENT.md are stale
`README.md` says `streamlit run app.py` and lists `app.py` as the entry. That
file was deleted in commit `f66beb7`. `DEPLOYMENT.md` instructs deploying
`new_order_app.py` (also deleted) and references the now-removed two-tab
layout. Actual entry: `streamlit_app.py`, with pages in `pages/`. Anyone
following the deploy guide today will misconfigure Streamlit Cloud.

### 4. v2 page fails to load without Supabase secrets
`pages/3_PA_Extractor.py:27` wraps Supabase imports in `try/except` and falls
back to standalone-only mode (`_ORDER_CONTEXT_AVAILABLE`). `pages/4_PA_Extractor_v2.py:32`
imports the same symbols unconditionally. If `SUPABASE_URL` / `SUPABASE_SERVICE_KEY`
aren't configured, v2 won't load at all while v1 still works as a standalone
extractor. Pick one stance.

### 5. `create_order` has no rollback on partial failure
`supabase_client.py:26` inserts the `orders` row first, then loops through
files uploading each to storage and inserting an `order_documents` row per
file. If upload fails on file 3 of 5, the order row and the first two
document rows are already committed. The order shows up in the queue with
half its docs and no way to recover except manual cleanup or full delete.

---

## Fix opportunistically

Annoying, code-quality, partial features. Won't bite immediately, but worth
clearing as you touch nearby code.

### 6. `extract_from_pdf` is duplicated between v1 and the shared module
`pages/3_PA_Extractor.py:66` reimplements `extract_from_pdf` instead of
importing from `extractor.py` like v2 does. Same logic, two places to keep
in sync.

### 7. Status state machine is one-way and incomplete
`pages/2_Order_Queue.py:_open_for_review` only flips `new → in_review`.
Re-opening a `submitted` order doesn't move it back. Re-publishing doesn't
either. There's no UI affordance for demoting a submitted order to
in_review or new. Either document that submitted is a terminal state, or
add the transitions.

### 8. Schema migration is partial / not self-contained
`migration_add_transaction_fields.sql` adds 4 columns but assumes the
`orders` and `order_documents` tables and the `order-documents` storage
bucket already exist. DEPLOYMENT.md alludes to "the table-creation query
you ran earlier" — that SQL isn't in the repo. Anyone reproducing the
deployment from scratch will fail.

### 9. Closer "Nicole" is listed as her own assistant
`assignment_rules.py:41` — `_STATIC_DEFAULTS["Nicole"] = {..., "assistant": "Nicole"}`.
A closer can't realistically also be her own assistant. Almost certainly a
data-entry error.

### 10. `delete_order` silently swallows storage-remove errors
`supabase_client.py:112` has `except Exception: pass` around the storage
delete. The intent ("don't block delete on a missing file") is reasonable,
but nothing is logged and the comment in DEPLOYMENT.md claims this
"keep[s] your free-tier usage under control" — the opposite of what
happens when a storage delete actually fails. Orphan PDFs accumulate
invisibly.

### 11. `intake_summary_html` is imported but never used
Both extractor pages import `intake_summary_html` from `extractor.py`, but
review-mode Publish only emits Text + CSV. Either wire HTML into the
publish flow (matching the standalone four-button export) or drop the
import.

---

## Note for later

Lower-priority fragility — worth being aware of, not worth a dedicated PR.

### 12. CSV column order is non-deterministic
`flatten_for_csv` iterates `for key in dates:` / `title_and_closing:` /
`mn_specific_disclosures:` — column order depends on whichever keys Claude
returned this run. If TPS import mapping ever depends on positional
columns, this will surface as intermittent breakage. Locking down an
explicit column order would fix it.

### 13. `MAX_TOKENS = 4096` is tight for addenda-heavy agreements
`extractor.py:27` and `pages/3_PA_Extractor.py:51` both cap output at 4096
tokens. A long agreement with several addenda can exceed this; the failure
surfaces to the user as a `JSONDecodeError` with a "try re-uploading"
message rather than a truncation explanation. Consider bumping the cap or
detecting truncation explicitly.
