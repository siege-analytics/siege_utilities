-- V0003 — redistricting_plans + plan_district_assignments
--
-- RedistrictingPlan maps Seats to boundary polygons for a window of
-- Congressional Terms (or, for non-federal offices, for a date range).
-- When a court strikes down a plan, effective_to is set and a new plan
-- takes over.
--
-- plan_district_assignments is the (plan, seat) → boundary mapping.
-- The boundary reference is polymorphic (generic-FK style) because the
-- boundary tables live in the consumer's schema (siege_utilities.geo
-- has CongressionalDistrict / StateLegislativeUpper / etc., but other
-- consumers may target their own boundary tables). The target table
-- name + row id are stored opaquely here.

-- --------------------------------------------------------------------
-- redistricting_plans
-- --------------------------------------------------------------------

CREATE TABLE political.redistricting_plans (
    id UUID PRIMARY KEY,

    jurisdiction_code TEXT NOT NULL,
    -- 'US-TX', 'US-CA-HARRIS', etc. Kept as TEXT since
    -- siege_utilities.political doesn't own a jurisdictions table
    -- (consumer's jurisdictions table holds the canonical record).

    plan_type TEXT NOT NULL
        CHECK (plan_type IN (
            'congressional',          -- US House districts
            'state_senate',
            'state_house',
            'state_legislative_joint', -- some states elect combined
            'city_council',
            'county_commission',
            'school_board',
            'water_district',
            'other'
        )),

    plan_name TEXT NOT NULL DEFAULT '',
    -- Official plan name / identifier (e.g., "Plan C2100", "HB 1").

    -- Time window — for federal plans, in terms of CongressionalTerm.
    -- For non-federal, effective dates are more useful (sessions vary).
    effective_from_congress SMALLINT NULL,
    effective_to_congress SMALLINT NULL,
    effective_from_date DATE NOT NULL,
    effective_to_date DATE NULL,
    -- NULL effective_to_date = still active.

    CONSTRAINT chk_redistricting_plans_date_order
        CHECK (effective_to_date IS NULL OR effective_from_date <= effective_to_date),
    CONSTRAINT chk_redistricting_plans_congress_range
        CHECK (
            (effective_from_congress IS NULL OR effective_from_congress BETWEEN 1 AND 300)
            AND (effective_to_congress IS NULL OR effective_to_congress BETWEEN 1 AND 300)
        ),
    CONSTRAINT chk_redistricting_plans_congress_order
        CHECK (effective_from_congress IS NULL
            OR effective_to_congress IS NULL
            OR effective_from_congress <= effective_to_congress),

    enacted_date DATE NULL,
    enacted_by TEXT NOT NULL DEFAULT ''
        CHECK (enacted_by IN (
            '', 'legislature', 'commission', 'court', 'special_master',
            'referendum', 'emergency_order', 'other'
        )),
    court_case TEXT NOT NULL DEFAULT '',
    -- For court-drawn plans: case citation or docket reference.

    notes TEXT NOT NULL DEFAULT '',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE political.redistricting_plans IS
    'Redistricting plan effective for a window of time. Court-struck plans have effective_to_date set and are succeeded by a new plan. Supports mid-cycle redistricting (court-ordered mid-decade changes).';

CREATE TRIGGER redistricting_plans_touch_updated_at
    BEFORE UPDATE ON political.redistricting_plans
    FOR EACH ROW EXECUTE FUNCTION political._touch_updated_at();

CREATE INDEX idx_redistricting_plans_jurisdiction_type
    ON political.redistricting_plans (jurisdiction_code, plan_type);
CREATE INDEX idx_redistricting_plans_active
    ON political.redistricting_plans (id)
    WHERE effective_to_date IS NULL;
CREATE INDEX idx_redistricting_plans_effective_from
    ON political.redistricting_plans (effective_from_date DESC);

-- --------------------------------------------------------------------
-- plan_district_assignments
-- --------------------------------------------------------------------

CREATE TABLE political.plan_district_assignments (
    id BIGSERIAL PRIMARY KEY,

    plan_id UUID NOT NULL
        REFERENCES political.redistricting_plans (id) ON DELETE CASCADE,
    seat_id UUID NOT NULL
        REFERENCES political.seats (id) ON DELETE RESTRICT,

    -- Polymorphic boundary reference (generic FK pattern).
    -- boundary_table: fully qualified table name in the consumer's DB
    --                 e.g., 'public.locations_congressionaldistrict',
    --                       'siege_geo.temporal_boundary'.
    -- boundary_row_id: the row's primary key in that table, stringified
    --                 so UUID and integer PKs both fit.
    -- boundary_vintage_year: Census vintage year for the polygon.
    boundary_table TEXT NOT NULL,
    boundary_row_id TEXT NOT NULL,
    boundary_vintage_year SMALLINT NULL
        CHECK (boundary_vintage_year IS NULL
            OR (boundary_vintage_year BETWEEN 1900 AND 2200)),

    -- When this assignment was first populated / last verified.
    assignment_source TEXT NOT NULL DEFAULT '',
    -- 'census_bureau', 'state_commission', 'court_order', 'manual_mapping', etc.

    notes TEXT NOT NULL DEFAULT '',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (plan_id, seat_id)
);

COMMENT ON TABLE political.plan_district_assignments IS
    'Maps (plan × seat) to a concrete boundary polygon via polymorphic boundary reference. The boundary_table + boundary_row_id tuple points at the consumer''s boundary table (could be siege_geo.temporal_boundary, a consumer Census table, etc.) — siege_utilities.political doesn''t own a boundary table so the reference is opaque here.';
COMMENT ON COLUMN political.plan_district_assignments.boundary_table IS
    'Fully qualified target table name. Validated by application logic; DB-level enforcement would require a check function that inspects information_schema.';

CREATE INDEX idx_pda_seat ON political.plan_district_assignments (seat_id);
CREATE INDEX idx_pda_boundary
    ON political.plan_district_assignments (boundary_table, boundary_row_id);
