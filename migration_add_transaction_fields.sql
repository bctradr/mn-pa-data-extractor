-- Migration: Add transaction-type fields to orders table
-- Run this in your Supabase SQL Editor BEFORE deploying the new code.

alter table orders add column if not exists transaction_type text;
alter table orders add column if not exists property_state text;
alter table orders add column if not exists is_new_construction boolean default false;
alter table orders add column if not exists template_name text;
