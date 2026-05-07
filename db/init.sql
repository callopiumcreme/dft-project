-- DFT Project — DB initialization
-- Full schema managed by Alembic migrations.
-- This file runs once on fresh container start.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Ensure UTC timezone
ALTER DATABASE dft SET timezone TO 'UTC';
