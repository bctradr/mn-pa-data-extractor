# MN PA Extractor & Title Tools — Project Context

## What this is
Internal title-company tooling for a Minnesota title-production team.
Currently includes:
- PA extractor (streamlit_app.py + pages/3_PA_Extractor.py + pages/4_PA_Extractor_v2.py)
  — turns purchase agreement PDFs into structured CSV/JSON for TPS import
- New Order workflow (pages/1_New_Order.py) — intake fields + file upload,
  creates an order row in Supabase
- Order Queue (pages/2_Order_Queue.py) — lists saved orders, launches review

Planned siblings (separate apps, shared backend):
- Title examiner tool
- Document drafting tool
- Lien waiver audit tool

## Stack
- Python + Streamlit (UI)
- Anthropic SDK for extraction (model: claude-sonnet-4-6)
- Supabase (Postgres tables: orders, order_documents; storage bucket: order-documents)
- Hosted on Streamlit Community Cloud

## Architectural principles
- Business logic lives in plain-Python modules (extractor.py, supabase_client.py,
  summary_generator.py, assignment_rules.py, transaction_categories.py, ui_theme.py)
  — NOT inside Streamlit page files.
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

## Known issues
See ISSUES.md in the repo root for a prioritized list of known bugs and
inconsistencies. Read it at the start of any session that touches the relevant
modules.

## Periodic review (quarterly)
Check whether: (1) shared modules are growing into a backend in disguise;
(2) UI is fighting Streamlit; (3) external access beyond the internal team is
needed; (4) concurrent users exceed ~20. If 2+ are yes, plan migration to a
separated frontend/backend architecture.
