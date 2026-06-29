# MN PA Extractor & Title Tools — Project Context

## What this is
Internal title-company tooling for a Minnesota title-production team.
Currently includes:
- PA extractor (streamlit_app.py + pages/3_PA_Extractor.py + pages/4_PA_Extractor_v2.py)
  — turns purchase agreement PDFs into structured CSV/JSON for TPS import
- New Order workflow (pages/1_New_Order.py) — intake fields + file upload,
  creates an order row in Supabase
- Order Queue (pages/2_Order_Queue.py) — lists saved orders, launches review
- Water Bill Tracker (pages/5_Water_Bills.py + water_bills.py) — creates and tracks
  water bill requests to municipalities; followup log; receives bill PDFs

Planned siblings (separate apps, shared backend):
- Title examiner tool
- Document drafting tool
- Lien waiver audit tool

## Stack
- Python + Streamlit (UI)
- Anthropic SDK for extraction (model: claude-sonnet-4-6)
- Supabase (Postgres tables: orders, order_documents, municipalities,
  water_bill_requests, water_bill_followups; storage buckets: order-documents,
  water-bills)
- Hosted on Streamlit Community Cloud

## Architectural principles
- Business logic lives in plain-Python modules (extractor.py, supabase_client.py,
  water_bills.py, summary_generator.py, assignment_rules.py, transaction_categories.py,
  ui_theme.py) — NOT inside Streamlit page files.
- Streamlit pages orchestrate UI only — they call into shared modules for anything
  that touches data, files, or LLMs.
- Single source of truth: shared functions live in one module and get imported,
  never re-implemented per page.
- New apps follow the same pattern: thin Streamlit page on top of shared modules.

## Conventions
- All Supabase calls go through supabase_client.py
- All Anthropic calls go through extractor.py (or a new domain module like
  drafting.py for new tools later)
- @st.cache_resource only on client initializers, not business logic
- Snake_case for DB columns and intake field keys
- Schema changes get a migration file in the repo root

## Out of scope right now
- Migration off Streamlit
- Migration off Supabase
- MCP server (revisit when 2+ apps need shared live data access)
- Auth beyond Streamlit secrets / Cloudflare Access
- Multi-model support (see below)

## Deferred: multi-model support

Multi-model support (GLM-5.2 via OpenRouter as a cheaper default) was attempted
in June 2026 and reverted. Key learning: **model swapping is not a config change
for this app.** Claude's extraction path sends PDFs natively as base64 document
blocks; models accessed via OpenRouter receive plain chat-completion calls with no
equivalent PDF-block support. A second provider requires a separate
document-ingestion pipeline (PDF → text extraction via PyMuPDF or similar) before
the model is ever called — it's a different architecture, not a different API key.

If multi-model is revisited:
- Use LiteLLM as the abstraction layer (eliminates hand-rolled ModelBackend /
  GLMClient boilerplate)
- Build a provider-aware ingestion step: native PDF blocks for Claude, text
  extraction + chat-completion for everything else
- Keep extraction quality as the primary metric — cost savings only matter if
  structured JSON output is reliable enough for TPS import without manual review

## Water Bill Tracker

Module structure:
- `water_bills.py` — all Supabase calls for the water bill domain (municipalities,
  requests, followups, storage). No Streamlit imports; pure business logic.
- `pages/5_Water_Bills.py` — Streamlit UI only; imports everything from water_bills.py.

Tables: `municipalities`, `water_bill_requests`, `water_bill_followups`
(see `supabase/migrations/003_water_bills.sql`). Seed data for test municipalities:
`data/municipalities_seed.sql`.

Storage bucket: `water-bills` (private). Create in the Supabase Dashboard before
first use of `upload_bill_pdf()`.

Two-table followup pattern: `water_bill_followups` is an append-only log of outreach
actions (sent, follow_up, phone_call, received, note). Each entry can advance the
parent `water_bill_requests.status` according to `_ACTION_TO_STATUS` in water_bills.py.
`updated_at` is bumped manually by `update_request()` — no DB trigger is needed.

Phase 2 deferred items (not yet implemented):
- Outbound email via Microsoft Graph / SendGrid
- Fax via Phaxio
- Auto-create a water bill request when a New Order is saved (see TODO comment in
  streamlit_app.py; the field-mapping logic is already in `create_request_from_order()`)

## Known issues
See ISSUES.md in the repo root for a prioritized list of known bugs and
inconsistencies. Read it at the start of any session that touches the relevant
modules.

## Periodic review (quarterly)
Check whether: (1) shared modules are growing into a backend in disguise;
(2) UI is fighting Streamlit; (3) external access beyond the internal team is
needed; (4) concurrent users exceed ~20. If 2+ are yes, plan migration to a
separated frontend/backend architecture.
