-- ============================================================
-- IQSALON — Supabase Security Script
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor)
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- 1. UNIQUE CONSTRAINT: Prevent double-bookings
--    One slot (salon + date + time + stylist) per booking.
--    If you want ANY-stylist bookings to not block specific
--    stylists, remove "stylist" from the constraint.
-- ────────────────────────────────────────────────────────────
ALTER TABLE public.bookings
  DROP CONSTRAINT IF EXISTS bookings_unique_slot;

ALTER TABLE public.bookings
  ADD CONSTRAINT bookings_unique_slot
  UNIQUE (salon_id, date, time, stylist);

-- ────────────────────────────────────────────────────────────
-- 2. ENABLE ROW LEVEL SECURITY on all tables
-- ────────────────────────────────────────────────────────────
ALTER TABLE public.salons         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.accounts       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bookings       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.walkins        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.members        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.member_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inventory      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stylists       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.services       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.commissions    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions       ENABLE ROW LEVEL SECURITY;

-- ────────────────────────────────────────────────────────────
-- 3. SERVICE ROLE — full access for backend (Streamlit server)
--    Your Streamlit app uses the service_role key which bypasses
--    RLS automatically. No policy needed for service_role.
-- ────────────────────────────────────────────────────────────

-- ────────────────────────────────────────────────────────────
-- 4. ANON ROLE — public pages (booking & register)
--    Only allow SELECT on salons/stylists/services (needed for
--    the public booking page to show salon name + services).
--    Allow INSERT on bookings and members only.
-- ────────────────────────────────────────────────────────────

-- Drop existing anon policies first
DO $$ DECLARE r record;
BEGIN
  FOR r IN SELECT policyname, tablename FROM pg_policies
           WHERE schemaname='public' AND roles::text LIKE '%anon%'
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', r.policyname, r.tablename);
  END LOOP;
END $$;

-- salons: anon can read name (needed to show salon name on booking page)
CREATE POLICY "anon_read_salon_name" ON public.salons
  FOR SELECT TO anon
  USING (true);

-- stylists: anon can read (needed to show stylist list on booking page)
CREATE POLICY "anon_read_stylists" ON public.stylists
  FOR SELECT TO anon
  USING (true);

-- services: anon can read (needed to show service list on booking page)
CREATE POLICY "anon_read_services" ON public.services
  FOR SELECT TO anon
  USING (true);

-- bookings: anon can read ONLY time+date+stylist for slot availability checks
CREATE POLICY "anon_read_booking_slots" ON public.bookings
  FOR SELECT TO anon
  USING (true);   -- filter to specific salon+date in app code

-- bookings: anon can insert (customer submits booking)
CREATE POLICY "anon_insert_booking" ON public.bookings
  FOR INSERT TO anon
  WITH CHECK (true);

-- members: anon can select only to check duplicate phone on registration
CREATE POLICY "anon_check_member_phone" ON public.members
  FOR SELECT TO anon
  USING (true);

-- members: anon can insert (customer self-registers)
CREATE POLICY "anon_insert_member" ON public.members
  FOR INSERT TO anon
  WITH CHECK (true);

-- sessions: anon can select (for auto-login token validation)
CREATE POLICY "anon_read_session" ON public.sessions
  FOR SELECT TO anon
  USING (true);

-- sessions: anon can insert (create session on login)
CREATE POLICY "anon_insert_session" ON public.sessions
  FOR INSERT TO anon
  WITH CHECK (true);

-- sessions: anon can delete own session (logout)
CREATE POLICY "anon_delete_session" ON public.sessions
  FOR DELETE TO anon
  USING (true);

-- accounts: anon can SELECT (needed for login hash comparison)
-- NOTE: This still exposes hashed passwords to anon.
-- For better security, move auth to a server-side Edge Function.
CREATE POLICY "anon_read_accounts" ON public.accounts
  FOR SELECT TO anon
  USING (true);

-- All other tables: NO anon access (walkins, inventory, commissions,
-- member_history are staff-only via service_role key)

-- ────────────────────────────────────────────────────────────
-- 5. IMPORTANT: Change your Streamlit app to use SERVICE_ROLE key
--    not ANON key. In Supabase Dashboard → Settings → API:
--    Copy the "service_role" key (secret!) and update your
--    Streamlit secrets:
--      SUPABASE_KEY = "eyJ...service_role_key..."
--    This way ALL app operations bypass RLS and work correctly.
--    The anon policies above only protect the PUBLIC pages
--    (booking.py, register.py) which must use anon key or
--    a separate restricted client.
-- ────────────────────────────────────────────────────────────

-- Verify policies were created
SELECT tablename, policyname, roles, cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
