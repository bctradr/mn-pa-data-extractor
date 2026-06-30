-- 004_municipalities_state.sql
-- Add state column to municipalities for MN/WI filtering and seed data.
-- Run before executing scripts/seed_municipalities.py.

alter table municipalities add column if not exists state text;

create index if not exists idx_municipalities_state on municipalities(state);
