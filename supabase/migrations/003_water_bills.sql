-- 003_water_bills.sql
-- Water Bill Tracker: municipalities, water_bill_requests, water_bill_followups
--
-- Run against the Supabase project before deploying pages/5_Water_Bills.py.
-- Also create the 'water-bills' storage bucket (private) in the Supabase
-- Dashboard before calling upload_bill_pdf().

-- ── Municipalities ────────────────────────────────────────────────────────────

create table if not exists municipalities (
    id               uuid        primary key default gen_random_uuid(),
    name             text        not null,
    preferred_method text,                   -- email | fax | phone | portal
    email            text,
    fax              text,
    portal_url       text,
    notes            text,
    lead_time_days   integer,               -- business days before closing to send request
    created_at       timestamptz not null default now()
);

-- ── Water Bill Requests ───────────────────────────────────────────────────────
-- Status lifecycle:
--   pending → sent → follow_up_sent → received
-- updated_at is bumped manually by water_bills.py (no DB trigger needed).

create table if not exists water_bill_requests (
    id                 uuid        primary key default gen_random_uuid(),
    order_id           uuid        references orders(id) on delete set null,
    file_number        text,
    property_address   text,
    current_owners     text,
    new_buyers         text,
    closing_date           date,
    send_by_date           date,       -- closing_date minus lead_time_days; set at creation
    lead_time_days_used    integer,    -- lead time value applied when send_by_date was calculated
    municipality_id    uuid        references municipalities(id) on delete set null,
    municipality_name  text,       -- denormalized so rows survive municipality edits
    request_method     text,       -- email | fax | phone | portal
    status             text        not null default 'pending',
    bill_pdf_path      text,       -- storage path in the 'water-bills' bucket
    closer_name        text,
    closer_email       text,
    closer_phone       text,
    assistant_name     text,
    assistant_email    text,
    assistant_phone    text,
    notes              text,
    created_at         timestamptz not null default now(),
    updated_at         timestamptz not null default now()
);

-- ── Water Bill Followups ──────────────────────────────────────────────────────
-- Each row logs one outreach action. The parent request's status is updated by
-- water_bills.log_followup() according to the _ACTION_TO_STATUS mapping.

create table if not exists water_bill_followups (
    id          uuid        primary key default gen_random_uuid(),
    request_id  uuid        not null references water_bill_requests(id) on delete cascade,
    action      text,       -- sent | follow_up | phone_call | received | note
    method      text,       -- email | fax | phone | portal (nullable for 'note')
    notes       text,
    logged_by   text,
    logged_at   timestamptz not null default now()
);

-- ── Indexes ───────────────────────────────────────────────────────────────────

create index if not exists idx_wbr_order_id     on water_bill_requests(order_id);
create index if not exists idx_wbr_status       on water_bill_requests(status);
create index if not exists idx_wbr_closing_date on water_bill_requests(closing_date);
create index if not exists idx_wbf_request_id   on water_bill_followups(request_id);
