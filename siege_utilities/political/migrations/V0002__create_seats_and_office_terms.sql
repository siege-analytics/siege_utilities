-- V0002 — seats + office_terms + congressional_terms
--
-- Implements the core "political identity + service period" primitives
-- from electinfo ontology §18 (referenced design; siege_utilities.political
-- is the generic substrate):
--
-- - seats:  political identity (office + state + district + senate_class).
--           TX-28 persists across redistricting cycles.
-- - office_terms:  generic service period on a Seat. Handles odd-term
--           offices (gov cycles, 3-year administrators, mid-term fills).
-- - congressional_terms:  US federal specialization, 2-year boundary
--           with senate_classes_up + is_presidential.
--
-- UUID primary keys per the deterministic UUID5 pattern. Downstream
-- consumers (e.g., enterprise) use siege_utilities.identifiers to
-- generate consistent UUIDs from their own ROOT_NAMESPACE.

-- --------------------------------------------------------------------
-- seats
-- --------------------------------------------------------------------

CREATE TABLE political.seats (
    id UUID PRIMARY KEY,

    office_code TEXT NOT NULL,
    -- 'PRESIDENT', 'US_SENATE', 'US_HOUSE', 'GOVERNOR', 'STATE_SENATE',
    -- 'STATE_HOUSE', 'MAYOR', 'COUNTY_COMMISSIONER', etc.

    state_code TEXT NULL
        CHECK (state_code IS NULL OR state_code ~ '^[A-Z]{2}$'),
    -- NULL for President / other non-state-scoped offices.

    district_label TEXT NOT NULL DEFAULT '',
    -- '28' for TX-28, '' for statewide offices.

    senate_class SMALLINT NULL
        CHECK (senate_class IS NULL OR senate_class IN (1, 2, 3)),
    -- 1/2/3 for US Senate. NULL for non-Senate seats.

    seat_label TEXT NOT NULL,
    -- Human-readable label: 'TX-28', 'US Senate TX Class 1', 'President', etc.
    -- Denormalized for display convenience.

    jurisdiction_code TEXT NOT NULL,
    -- 'FEC' for federal, state code otherwise. Denormalized so this
    -- table is consumable without requiring a consumer-specific
    -- jurisdictions table.

    notes TEXT NOT NULL DEFAULT '',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

);

COMMENT ON TABLE political.seats IS
    'Political seat identity — persists across redistricting cycles. TX-28 as a label exists as long as Texas has 28+ districts; what polygon it covers changes per RedistrictingPlan.';

CREATE TRIGGER seats_touch_updated_at
    BEFORE UPDATE ON political.seats
    FOR EACH ROW EXECUTE FUNCTION political._touch_updated_at();

-- Seat natural-key uniqueness. A plain UNIQUE (office_code, state_code, district_label,
-- senate_class) would allow duplicates when state_code or senate_class is NULL because
-- PostgreSQL treats NULL as distinct in UNIQUE indexes. COALESCE normalizes NULLs to
-- sentinel values ('', -1) so every seat gets exactly one row.
CREATE UNIQUE INDEX uq_seats_natural_key
    ON political.seats (
        office_code,
        COALESCE(state_code, ''),
        district_label,
        COALESCE(senate_class, -1)
    );

CREATE INDEX idx_seats_office_state
    ON political.seats (office_code, state_code);
CREATE INDEX idx_seats_senate_class
    ON political.seats (senate_class)
    WHERE senate_class IS NOT NULL;
CREATE INDEX idx_seats_jurisdiction
    ON political.seats (jurisdiction_code);

-- --------------------------------------------------------------------
-- office_terms (generic)
-- --------------------------------------------------------------------

CREATE TABLE political.office_terms (
    id UUID PRIMARY KEY,

    seat_id UUID NOT NULL
        REFERENCES political.seats (id) ON DELETE RESTRICT,

    -- Downstream consumers FK incumbent_agent_id into their own agents
    -- table. Left as UUID without FK here because siege_utilities is
    -- domain-agnostic and doesn't know what "agent" means in the
    -- consumer schema. Consumer migrations add the FK.
    incumbent_agent_id UUID NULL,

    term_start DATE NOT NULL,
    term_end DATE NULL,
    -- NULL while incumbent still holds office.

    scheduled_end DATE NOT NULL,
    -- What the term was scheduled to end, if nothing interrupted.
    -- Often equal to term_end; differs when a term ends early
    -- (resignation, death, recall, removal).

    end_cause TEXT NULL
        CHECK (end_cause IS NULL
            OR end_cause IN (
                'scheduled',
                'resignation',
                'death',
                'recall',
                'removal',
                'court_order',
                'appointment_ended',
                'seat_abolished',
                'other'
            )),
    -- NULL while term_end IS NULL; required when term_end set.

    CONSTRAINT chk_office_terms_end_pair
        CHECK ((term_end IS NULL AND end_cause IS NULL)
            OR (term_end IS NOT NULL AND end_cause IS NOT NULL)),
    CONSTRAINT chk_office_terms_date_order
        CHECK (term_end IS NULL OR term_start <= term_end),

    -- Produced-by-election link. UUID without FK for the same reason
    -- as incumbent_agent_id.
    produced_by_election_id UUID NULL,

    -- Chain for same seat. The compound FK (next_term_id, seat_id) references
    -- the UNIQUE (id, seat_id) on this table — enforcing that next_term_id,
    -- when set, must belong to the same seat. NULL next_term_id is exempt.
    next_term_id UUID NULL,

    notes TEXT NOT NULL DEFAULT '',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Composite UNIQUE enables specialization (congressional_terms
    -- below) via composite FK.
    UNIQUE (id, seat_id)
);

-- Enforce the same-seat invariant on next_term_id. The compound FK references
-- UNIQUE (id, seat_id) on this same table: when next_term_id is not NULL it must
-- point at a row whose seat_id matches the current row's seat_id.
ALTER TABLE political.office_terms
    ADD CONSTRAINT fk_office_terms_next_same_seat
        FOREIGN KEY (next_term_id, seat_id)
        REFERENCES political.office_terms (id, seat_id)
        ON DELETE SET NULL;

COMMENT ON TABLE political.office_terms IS
    'Generic service period on a Seat. Handles odd-term offices (2-year NH/VT gov, 4-year most states, 5-year some appointed positions, 3-year administrator rotations, mid-term fills from specials).';
COMMENT ON COLUMN political.office_terms.incumbent_agent_id IS
    'UUID of the Person holding this term. FK added by downstream consumer migration (siege_utilities doesn''t own an Agents table).';
COMMENT ON COLUMN political.office_terms.produced_by_election_id IS
    'UUID of the Election that produced this term (if any — appointed terms have NULL). FK added by downstream consumer migration.';

CREATE TRIGGER office_terms_touch_updated_at
    BEFORE UPDATE ON political.office_terms
    FOR EACH ROW EXECUTE FUNCTION political._touch_updated_at();

CREATE INDEX idx_office_terms_seat_start
    ON political.office_terms (seat_id, term_start DESC);
CREATE INDEX idx_office_terms_incumbent
    ON political.office_terms (incumbent_agent_id)
    WHERE incumbent_agent_id IS NOT NULL;
CREATE INDEX idx_office_terms_current
    ON political.office_terms (seat_id)
    WHERE term_end IS NULL;
CREATE INDEX idx_office_terms_produced_by_election
    ON political.office_terms (produced_by_election_id)
    WHERE produced_by_election_id IS NOT NULL;

-- --------------------------------------------------------------------
-- congressional_terms (US federal specialization)
-- --------------------------------------------------------------------

CREATE TABLE political.congressional_terms (
    office_term_id UUID PRIMARY KEY,
    seat_id UUID NOT NULL,

    congress_number SMALLINT NOT NULL
        CHECK (congress_number >= 1 AND congress_number <= 300),
    -- 1st Congress through (eventually) the 300th. Generous upper bound.
    -- Uniqueness is (congress_number, seat_id) — see partial index below.

    senate_classes_up SMALLINT[] NOT NULL DEFAULT ARRAY[]::SMALLINT[],
    -- Array of Senate classes with seats up for election in this
    -- Congress's election year (typically 1, 2, or 3 element arrays).
    -- Empty for terms that don't coincide with a Senate election cycle.

    is_presidential BOOLEAN NOT NULL,
    -- TRUE if this Congress's term begins in a presidential
    -- inauguration year (odd years following presidential election).

    election_year SMALLINT NOT NULL
        CHECK (election_year BETWEEN 1788 AND 2200),
    -- Year of the general election that produced this term (even year).

    FOREIGN KEY (office_term_id, seat_id)
        REFERENCES political.office_terms (id, seat_id)
        ON DELETE CASCADE
);

CREATE UNIQUE INDEX uq_congressional_terms_congress_seat
    ON political.congressional_terms (congress_number, seat_id);

COMMENT ON TABLE political.congressional_terms IS
    'US federal specialization of OfficeTerm. 2-year boundary anchored by congress_number. Every OfficeTerm for a federal House/Senate/Presidential Seat has a matching row here.';
COMMENT ON COLUMN political.congressional_terms.senate_classes_up IS
    'Senate classes (1,2,3) with seats up for election in this Congress''s cycle. Empty for terms that don''t coincide with a Senate election cycle.';

CREATE INDEX idx_congressional_terms_election_year
    ON political.congressional_terms (election_year);
CREATE INDEX idx_congressional_terms_presidential
    ON political.congressional_terms (is_presidential)
    WHERE is_presidential;
