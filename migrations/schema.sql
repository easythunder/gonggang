"""PostgreSQL schema for Meet-Match (manual setup script).

Run with: psql -U gonggang -d gonggang -f migrations/schema.sql
"""

-- Create ENUM types
CREATE TYPE submission_status AS ENUM ('success', 'failed', 'pending');

-- Create groups table
CREATE TABLE groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    display_unit_minutes INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_activity_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    admin_token VARCHAR(255) NOT NULL UNIQUE,
    invite_url VARCHAR(500) NOT NULL UNIQUE,
    share_url VARCHAR(500) NOT NULL UNIQUE,
    max_participants INTEGER NOT NULL DEFAULT 50,
    CHECK (display_unit_minutes IN (10, 20, 30, 60))
);

CREATE INDEX ix_groups_expires_at ON groups(expires_at);
CREATE INDEX ix_groups_last_activity ON groups(last_activity_at);

-- Create submissions table
CREATE TABLE submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    nickname VARCHAR(255) NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    status submission_status NOT NULL DEFAULT 'pending',
    error_reason VARCHAR(500),
    UNIQUE(group_id, nickname)
);

CREATE INDEX ix_submissions_group_id ON submissions(group_id);
CREATE INDEX ix_submissions_status ON submissions(status);

-- Create intervals table (5-minute slot based)
CREATE TABLE intervals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6),
    start_minute INTEGER NOT NULL CHECK (start_minute >= 0 AND start_minute <= 1435),
    end_minute INTEGER NOT NULL CHECK (end_minute >= 5 AND end_minute <= 1440),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CHECK (start_minute < end_minute),
    CHECK (start_minute % 5 = 0),  -- 5-minute aligned
    CHECK (end_minute % 5 = 0)     -- 5-minute aligned
);

CREATE INDEX ix_intervals_submission_id ON intervals(submission_id);
CREATE INDEX ix_intervals_day_slot ON intervals(day_of_week, start_minute, end_minute);

-- Create free time results table
CREATE TABLE group_free_time_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL UNIQUE REFERENCES groups(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    availability_by_day JSONB,              -- Grid structure
    free_time_intervals JSONB,              -- 기본: ≥10분 자유시간
    free_time_intervals_30min JSONB,        -- ≥30분 자유시간
    free_time_intervals_60min JSONB,        -- ≥60분 자유시간
    computed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    status submission_status NOT NULL DEFAULT 'pending',
    error_code VARCHAR(100)
);

CREATE INDEX ix_free_time_group ON group_free_time_results(group_id);
CREATE INDEX ix_free_time_computed ON group_free_time_results(computed_at);

-- Create deletion logs table (audit trail)
CREATE TABLE deletion_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID REFERENCES groups(id) ON DELETE SET NULL,
    deleted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    reason VARCHAR(100) NOT NULL,
    submission_count INTEGER,
    asset_count INTEGER,
    error_code VARCHAR(100),
    retry_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX ix_deletion_logs_group ON deletion_logs(group_id);
CREATE INDEX ix_deletion_logs_deleted_at ON deletion_logs(deleted_at);
CREATE INDEX ix_deletion_logs_reason ON deletion_logs(reason);

-- Post-creation verification
SELECT 'Schema created successfully' AS status;
SELECT count(*) as table_count FROM information_schema.tables WHERE table_schema = 'public';
