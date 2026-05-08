-- ============================================================
-- Signature Kim SaaS — Supabase Schema
-- Run this in Supabase > SQL Editor > New Query
-- ============================================================

-- Salons (branches)
create table if not exists salons (
  id          text primary key,
  name        text not null,
  created_at  timestamptz default now()
);

-- Accounts
create table if not exists accounts (
  username      text primary key,
  password_hash text not null,
  role          text not null default 'staff',   -- owner | manager | staff
  salon_id      text references salons(id) on delete set null,
  display_name  text,
  created_at    timestamptz default now()
);

-- Stylists
create table if not exists stylists (
  id        uuid default gen_random_uuid() primary key,
  salon_id  text references salons(id) on delete cascade,
  name      text not null
);

-- Bookings
create table if not exists bookings (
  id         uuid default gen_random_uuid() primary key,
  salon_id   text references salons(id) on delete cascade,
  name       text,
  phone      text default '',
  date       text,
  time       text,
  stylist    text default '',
  service    text default '',
  note       text default '',
  price      numeric default 0,
  paid       boolean default false,
  method     text default '',
  final      numeric default 0,
  source     text default 'staff',   -- 'staff' | 'online'
  status     text default 'confirmed', -- 'confirmed' | 'pending' | 'cancelled'
  created_at timestamptz default now()
);

-- Add new columns to existing table (run if table already exists)
alter table bookings add column if not exists phone text default '';
alter table bookings add column if not exists email text default '';
alter table bookings add column if not exists source text default 'staff';
alter table bookings add column if not exists status text default 'confirmed';

-- Walk-ins
create table if not exists walkins (
  id         uuid default gen_random_uuid() primary key,
  salon_id   text references salons(id) on delete cascade,
  name       text,
  service    text default '',
  date       text,
  final      numeric default 0,
  method     text default 'Cash',
  created_at timestamptz default now()
);

-- Inventory
create table if not exists inventory (
  id        uuid default gen_random_uuid() primary key,
  salon_id  text references salons(id) on delete cascade,
  name      text,
  category  text default '',
  qty       integer default 0,
  max       integer default 20,
  unit      text default '瓶'
);

-- Members
create table if not exists members (
  id           text primary key,
  salon_id     text references salons(id) on delete cascade,
  name         text,
  phone        text default '',
  birthday     text default '',
  tier         text default '普通',
  points       integer default 0,
  total_spent  numeric default 0,
  visit_count  integer default 0,
  notes        text default '',
  join_date    text,
  created_at   timestamptz default now()
);

-- Member spending history
create table if not exists member_history (
  id         uuid default gen_random_uuid() primary key,
  member_id  text references members(id) on delete cascade,
  date       text,
  service    text,
  amt        numeric,
  pts        integer
);


-- ============================================================
-- SUBSCRIPTION COLUMNS (run if tables already exist)
-- ============================================================
alter table salons add column if not exists plan         text    default 'trial';
alter table salons add column if not exists trial_ends   date    default (current_date + interval '30 days');
alter table salons add column if not exists plan_ends    date;
alter table salons add column if not exists stripe_link  text    default '';
alter table salons add column if not exists contact_name text    default '';
alter table salons add column if not exists contact_phone text   default '';
alter table salons add column if not exists contact_email text   default '';

-- ============================================================
-- SEED DATA — First salon + admin account
-- Replace password_hash with: sha256('your_password')
-- You can generate it at: https://emn178.github.io/online-tools/sha256.html
-- Default password below is: admin123
-- ============================================================

insert into salons (id, name) values
  ('B001', 'Signature Kim — KL')
on conflict do nothing;

-- Role values: 'admin' | 'owner' | 'manager' | 'staff'
-- admin = IQSALON platform admin (highest level)
-- owner = salon owner (manages own branches)
insert into accounts (username, password_hash, role, salon_id, display_name) values
  ('iqsalon', 'a8f74cdcb9c76c79ad89fa90ad27c3f6f04c9e614c02a72e43a1a4e0a1b2c3d4', 'admin',   null,   'IQSALON Admin'),
  ('admin',   '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'owner',   null,   'Admin'),
  ('kim',     'a5c5c5ffc8e3aff01e83f4de81b7c3c2e35f4b26c1e5b22e527ea26f2d2d5e7f', 'manager', 'B001', 'Kim'),
  ('lily',    'f4dc9a0a8a39a1acfea8f5fcf7bcbe3dc7f46ffc0d2a2ae66a0b4cc1feceecd1', 'staff',   'B001', 'Lily')
on conflict do nothing;

insert into stylists (salon_id, name) values
  ('B001', 'Kim'), ('B001', 'Lily'), ('B001', 'Jason')
on conflict do nothing;
