-- PRAHARI Database Schema
-- Auto-executed on first Postgres container start via docker-entrypoint-initdb.d

-- Fused alerts from the Identity Fusion Job + Fusion Classifier
CREATE TABLE IF NOT EXISTS alerts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id     VARCHAR(64)  NOT NULL,
    fusion_score    FLOAT        NOT NULL,
    severity        VARCHAR(10)  NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    contributing_signals JSONB   NOT NULL DEFAULT '[]',
    explanation     TEXT,
    regulatory_controls  JSONB   DEFAULT '[]',
    window_start    TIMESTAMPTZ  NOT NULL,
    window_end      TIMESTAMPTZ  NOT NULL,
    scenario_type   VARCHAR(50),
    is_synthetic_positive BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ  DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  DEFAULT NOW()
);

-- Quantum / HNDL alerts from Crypto Inventory Job
CREATE TABLE IF NOT EXISTS quantum_alerts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      VARCHAR(64)  NOT NULL,
    key_exchange    VARCHAR(32)  NOT NULL,
    signature_algo  VARCHAR(32)  NOT NULL,
    classification  VARCHAR(16)  NOT NULL CHECK (classification IN ('legacy', 'pqc_ready', 'hybrid')),
    is_hndl_exposed BOOLEAN      DEFAULT FALSE,
    data_sensitivity VARCHAR(32) NOT NULL,
    bytes_transferred BIGINT     DEFAULT 0,
    destination     VARCHAR(16)  NOT NULL,
    risk_factors    JSONB        DEFAULT '[]',
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

-- Case management — analyst actions on alerts (Section 9 Level 3)
CREATE TABLE IF NOT EXISTS cases (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id    UUID         NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    status      VARCHAR(20)  NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'acknowledged', 'escalated', 'dismissed')),
    assigned_to VARCHAR(128),
    notes       TEXT,
    created_at  TIMESTAMPTZ  DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  DEFAULT NOW()
);

-- Immutable audit trail for every case action (Section 9 Level 3)
CREATE TABLE IF NOT EXISTS audit_trail (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(32)  NOT NULL,
    entity_id   UUID         NOT NULL,
    action      VARCHAR(32)  NOT NULL,
    actor       VARCHAR(128) NOT NULL DEFAULT 'system',
    details     JSONB        DEFAULT '{}',
    created_at  TIMESTAMPTZ  DEFAULT NOW()
);

-- Identity behavioural profiles (backing store for Redis cache, Section 5)
CREATE TABLE IF NOT EXISTS identity_profiles (
    identity_id             VARCHAR(64) PRIMARY KEY,
    known_devices           JSONB   DEFAULT '[]',
    known_beneficiaries     JSONB   DEFAULT '[]',
    known_ips               JSONB   DEFAULT '[]',
    avg_txn_amount          FLOAT   DEFAULT 0,
    txn_count               INTEGER DEFAULT 0,
    login_time_distribution JSONB   DEFAULT '{}',
    risk_score              FLOAT   DEFAULT 0,
    last_seen_geo           JSONB   DEFAULT '{}',
    last_updated            TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for dashboard queries (Section 5 — KPI aggregates)
CREATE INDEX idx_alerts_identity   ON alerts(identity_id);
CREATE INDEX idx_alerts_severity   ON alerts(severity);
CREATE INDEX idx_alerts_created    ON alerts(created_at DESC);
CREATE INDEX idx_alerts_score      ON alerts(fusion_score DESC);
CREATE INDEX idx_quantum_session   ON quantum_alerts(session_id);
CREATE INDEX idx_quantum_hndl      ON quantum_alerts(is_hndl_exposed) WHERE is_hndl_exposed = TRUE;
CREATE INDEX idx_quantum_created   ON quantum_alerts(created_at DESC);
CREATE INDEX idx_cases_status      ON cases(status);
CREATE INDEX idx_cases_alert       ON cases(alert_id);
CREATE INDEX idx_audit_entity      ON audit_trail(entity_type, entity_id);
CREATE INDEX idx_audit_created     ON audit_trail(created_at DESC);
