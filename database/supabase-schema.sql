-- Allin Barometr: optional bootstrap only. The backend creates current tables.
-- Run on the NEW project's database, with a role that can create schemas.
create schema if not exists allin_barometr;
revoke all on schema allin_barometr from public, anon, authenticated;
-- Do not expose allin_barometr or venue_* through the Supabase Data API.
-- Each venue's schema is provisioned by the owner application's Create venue action.
