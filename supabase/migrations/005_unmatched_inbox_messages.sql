-- 005_unmatched_inbox_messages.sql
-- Stores inbound Gmail messages that could not be matched to any active
-- water bill request (no file number or property address signal found).
-- Run after 003_water_bills.sql.

create table if not exists water_bill_unmatched_messages (
    id               uuid        primary key default gen_random_uuid(),
    gmail_message_id text        unique,       -- deduplicates repeated inbox checks
    from_address     text,
    subject          text,
    body_preview     text,                     -- first 500 chars of plain-text body
    received_at      text,                     -- raw Gmail Date header (not parsed)
    checked_at       timestamptz not null default now()
);

create index if not exists idx_wbum_checked_at on water_bill_unmatched_messages(checked_at);
