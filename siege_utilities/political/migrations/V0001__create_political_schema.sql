-- V0001 — create the political schema
--
-- Schema-level container for siege_utilities.political tables. Consumer
-- projects point the MigrationRunner's tracking_schema='political' so
-- the _schema_migrations tracking table also lives here, keeping all
-- siege_utilities.political migration state co-located.

CREATE SCHEMA IF NOT EXISTS political;

COMMENT ON SCHEMA political IS
    'siege_utilities.political — generic political-infrastructure primitives (Seat, OfficeTerm, RedistrictingPlan, StateElectionCalendar). Reusable across projects. Managed by siege_utilities.schema.MigrationRunner.';

-- Shared trigger function for updated_at columns. Mirrors the pattern
-- in enterprise._touch_updated_at but lives in this schema so
-- downstream consumers don't depend on a specific consumer's schema.
CREATE OR REPLACE FUNCTION political._touch_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION political._touch_updated_at() IS
    'Set updated_at = NOW() on BEFORE UPDATE triggers. Reusable across political.* tables.';
