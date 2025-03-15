#!/bin/bash
# Script to set up the hades database for testing

# Create the hades_db database owned by the hades user
echo "Creating hades_db database owned by hades user..."
sudo -u postgres createdb -O hades hades_db

# Create the hades_test database for testing
echo "Creating hades_test database for testing..."
sudo -u postgres createdb -O hades hades_test

# Set up test tables in the hades_test database
echo "Setting up test tables in hades_test database..."
sudo -u postgres psql -d hades_test -c "
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
"

echo "Database setup complete!"
