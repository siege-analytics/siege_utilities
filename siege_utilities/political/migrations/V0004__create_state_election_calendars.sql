-- V0004 — state_election_calendars
--
-- Per-state, per-CongressionalTerm election administration dates.
-- TX primary in March; CA may use jungle primary; GA has a runoff
-- threshold; each state has different registration / early-voting /
-- mail-ballot rules.
--
-- Typically seeded from a trusted source (NCSL compilation, Ballot
-- Access News, the state Secretary of State's office) per cycle.

CREATE TABLE political.state_election_calendars (
    id UUID PRIMARY KEY,

    state_code TEXT NOT NULL
        CHECK (state_code ~ '^[A-Z]{2}$'),

    congress_number SMALLINT NOT NULL
        CHECK (congress_number >= 1 AND congress_number <= 300),

    election_year SMALLINT NOT NULL
        CHECK (election_year BETWEEN 1788 AND 2200),

    -- Primary
    primary_date DATE NULL,
    primary_type TEXT NULL
        CHECK (primary_type IS NULL OR primary_type IN (
            'open',
            'closed',
            'semi_closed',      -- unaffiliated may vote; party members fixed
            'blanket',          -- vote for any candidate regardless of party
            'jungle',           -- top-two advance regardless of party (CA/WA)
            'louisiana',        -- majority-wins-or-runoff (LA)
            'other'
        )),
    primary_runoff_date DATE NULL,
    primary_runoff_threshold_pct NUMERIC(5, 2) NULL
        CHECK (primary_runoff_threshold_pct IS NULL
            OR (primary_runoff_threshold_pct > 0 AND primary_runoff_threshold_pct <= 100)),
    -- Some states require a runoff if no candidate receives >50%
    -- (threshold=50.00). Others use lower thresholds.

    -- General
    general_date DATE NOT NULL,
    -- "first Tuesday after first Monday in November" — deterministic
    -- but stored explicitly per cycle for cross-check.
    general_runoff_date DATE NULL,

    -- Registration + voting windows
    registration_deadline DATE NULL,
    early_voting_start DATE NULL,
    early_voting_end DATE NULL,
    mail_ballot_request_deadline DATE NULL,
    mail_ballot_receipt_deadline DATE NULL,

    -- Certification
    certification_deadline DATE NULL,

    -- Source + provenance
    source_citation TEXT NOT NULL DEFAULT '',
    -- E.g., "NCSL 2024 Election Calendar", "TX Election Code §41.007".

    notes TEXT NOT NULL DEFAULT '',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (state_code, congress_number)
);

COMMENT ON TABLE political.state_election_calendars IS
    'Per-state, per-CongressionalTerm election administration dates (primary, general, runoff, registration deadlines, early voting windows, certification). Populated per cycle from NCSL + state SoS sources.';

CREATE TRIGGER state_election_calendars_touch_updated_at
    BEFORE UPDATE ON political.state_election_calendars
    FOR EACH ROW EXECUTE FUNCTION political._touch_updated_at();

CREATE INDEX idx_sec_state ON political.state_election_calendars (state_code);
CREATE INDEX idx_sec_congress ON political.state_election_calendars (congress_number);
CREATE INDEX idx_sec_primary_date
    ON political.state_election_calendars (primary_date)
    WHERE primary_date IS NOT NULL;
CREATE INDEX idx_sec_general_date
    ON political.state_election_calendars (general_date);
