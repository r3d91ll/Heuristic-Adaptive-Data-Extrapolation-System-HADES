-- PostgreSQL setup script for HADES testing
-- Run this script as the postgres user with:
-- psql -f setup_hades_db.sql

-- Create the hades user if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'hades') THEN
        CREATE USER hades WITH PASSWORD 'o$n^3W%QD0HGWxH!';
        ALTER USER hades CREATEDB;
    ELSE
        ALTER USER hades WITH PASSWORD 'o$n^3W%QD0HGWxH!';
    END IF;
END
$$;

-- Create the hades_test database if it doesn't exist
SELECT 'CREATE DATABASE hades_test OWNER hades'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'hades_test')
\gexec

-- Connect to the hades_test database
\c hades_test

-- Create tables for authentication
CREATE TABLE IF NOT EXISTS api_keys (
    key_id VARCHAR(64) PRIMARY KEY,
    key_hash VARCHAR(128) NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS rate_limits (
    key_id VARCHAR(64) REFERENCES api_keys(key_id),
    endpoint VARCHAR(255) NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    window_start TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (key_id, endpoint)
);

-- Grant privileges to hades user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO hades;

-- Output success message
\echo 'PostgreSQL setup completed successfully!'
\echo 'User ''hades'' and database ''hades_test'' are ready for testing.'
