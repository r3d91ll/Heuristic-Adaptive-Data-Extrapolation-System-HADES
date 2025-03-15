# PostgreSQL Setup Instructions for HADES

This guide will help you set up the PostgreSQL database with the dedicated `hades` user for testing the HADES system.

## 1. Fix the PostgreSQL Role Password

The system user `hades` has been created, but there might be an issue with the PostgreSQL role password. Let's fix it:

```bash
# Connect to PostgreSQL as the postgres user
sudo -u postgres psql

# In the PostgreSQL prompt, run:
ALTER USER hades WITH PASSWORD 'o$n^3W%QD0HGWxH!';
\q
```

## 2. Create the Test Database

```bash
# Create the hades_test database owned by the hades user
sudo -u postgres psql -c "CREATE DATABASE hades_test OWNER hades;"
```

## 3. Create the Required Tables

```bash
# Create the tables in the hades_test database
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

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO hades;
"
```

## 4. Update PostgreSQL Authentication Configuration

Edit the PostgreSQL authentication configuration file to allow password authentication for the hades user:

```bash
# Find the pg_hba.conf file
sudo find /etc/postgresql -name pg_hba.conf

# Edit the file (replace with the actual path)
sudo nano /etc/postgresql/*/main/pg_hba.conf

# Add the following line before the existing 'host all' entries:
# host    hades_test    hades    127.0.0.1/32    md5

# Save and exit (Ctrl+O, Enter, Ctrl+X)

# Restart PostgreSQL
sudo systemctl restart postgresql
```

## 5. Verify the PostgreSQL Connection

Run the verification script to check if the connection works:

```bash
cd ~/ML-Lab/Heuristic-Adaptive-Data-Extrapolation-System-HADES
source venv/bin/activate
python tests/verify_pg_connection.py
```

## 6. Run the Tests

If the verification is successful, you can run the tests:

```bash
cd ~/ML-Lab/Heuristic-Adaptive-Data-Extrapolation-System-HADES
./tests/run_pg_tests.sh
```

## Troubleshooting

If you still encounter issues with the PostgreSQL connection:

1. Check if the password in your `.env.test` file matches the one you set for the hades user:
   ```
   HADES_TEST_DB_PASSWORD=o$n^3W%QD0HGWxH!
   ```

2. Try connecting to PostgreSQL directly with the hades user:
   ```bash
   psql -U hades -d hades_test -h localhost
   # When prompted, enter the password: o$n^3W%QD0HGWxH!
   ```

3. Check the PostgreSQL logs for more details:
   ```bash
   sudo tail -f /var/log/postgresql/postgresql-*.log
   ```
