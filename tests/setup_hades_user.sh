#!/bin/bash
# Setup script for creating the hades system user and PostgreSQL role
# This script requires sudo privileges

echo "Setting up hades system user and PostgreSQL role..."

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run with sudo privileges."
    echo "Please run: sudo ./setup_hades_user.sh"
    exit 1
fi

# Create the hades system user if it doesn't exist
if id "hades" &>/dev/null; then
    echo "System user 'hades' already exists."
else
    echo "Creating system user 'hades'..."
    useradd -m -s /bin/bash hades
    echo "Setting password for 'hades' user..."
    # Generate a secure password
    HADES_PASSWORD=$(openssl rand -base64 12)
    echo "hades:$HADES_PASSWORD" | chpasswd
    echo "Generated password for hades user: $HADES_PASSWORD"
    echo "Please save this password securely!"
fi

# Add the hades user to the postgres group
usermod -a -G postgres hades
echo "Added hades user to postgres group."

# Create PostgreSQL role for hades if it doesn't exist
echo "Creating PostgreSQL role for hades..."
su - postgres -c "psql -c \"DO \\\$\\\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'hades') THEN
        CREATE USER hades WITH PASSWORD 'o\$n^3W%QD0HGWxH!';
        ALTER USER hades CREATEDB;
    ELSE
        ALTER USER hades WITH PASSWORD 'o\$n^3W%QD0HGWxH!';
    END IF;
END
\\\$\\\$;\""

# Create the hades_test database if it doesn't exist
echo "Creating PostgreSQL database 'hades_test'..."
su - postgres -c "psql -c \"SELECT 'CREATE DATABASE hades_test OWNER hades' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'hades_test')\gexec\""

# Create the tables in the hades_test database
echo "Creating tables in 'hades_test' database..."
su - postgres -c "psql -d hades_test -c \"
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
\""

# Update the pg_hba.conf file to allow password authentication for the hades user
echo "Updating PostgreSQL authentication configuration..."
PG_HBA_CONF=$(find /etc/postgresql -name pg_hba.conf | head -n 1)

if [ -n "$PG_HBA_CONF" ]; then
    # Check if the entry already exists
    if ! grep -q "host.*hades_test.*hades.*md5" "$PG_HBA_CONF"; then
        # Add the entry for password authentication
        echo "host    hades_test    hades    127.0.0.1/32    md5" >> "$PG_HBA_CONF"
        echo "Added password authentication entry for hades user."
        
        # Restart PostgreSQL to apply changes
        systemctl restart postgresql
        echo "Restarted PostgreSQL service."
    else
        echo "Password authentication for hades user already configured."
    fi
else
    echo "Warning: Could not find pg_hba.conf file. You may need to manually update it."
    echo "Add the following line to your pg_hba.conf file:"
    echo "host    hades_test    hades    127.0.0.1/32    md5"
    echo "Then restart PostgreSQL with: sudo systemctl restart postgresql"
fi

# Update the .env.test file with the hades credentials
echo "Updating .env.test file with hades credentials..."
cat > /home/todd/ML-Lab/Heuristic-Adaptive-Data-Extrapolation-System-HADES/.env.test << EOL
# PostgreSQL credentials for testing
HADES_TEST_DB_NAME=hades_test
HADES_TEST_DB_USER=hades
HADES_TEST_DB_PASSWORD=o\$n^3W%QD0HGWxH!
HADES_TEST_DB_HOST=localhost
HADES_TEST_DB_PORT=5432

# Test environment settings
HADES_ENV=test
ENABLE_AUTH=true
EOL

# Set proper ownership and permissions
chown todd:todd /home/todd/ML-Lab/Heuristic-Adaptive-Data-Extrapolation-System-HADES/.env.test
chmod 600 /home/todd/ML-Lab/Heuristic-Adaptive-Data-Extrapolation-System-HADES/.env.test

echo "Setup completed successfully!"
echo "System user 'hades' and PostgreSQL role 'hades' are ready for use."
echo "The hades_test database has been created and configured."
echo "The .env.test file has been updated with the correct credentials."
echo ""
echo "You can now run the tests with: ./tests/run_pg_tests.sh"

exit 0
