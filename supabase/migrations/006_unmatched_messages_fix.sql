-- 006_unmatched_messages_fix.sql
-- Adds missing columns to water_bill_unmatched_messages.
-- received_at remains text (raw Gmail Date header); sort on checked_at instead.

alter table water_bill_unmatched_messages
    add column if not exists status            text default 'new',
    add column if not exists linked_request_id uuid references water_bill_requests(id);
