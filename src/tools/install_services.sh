#!/bin/bash
#
# HADES Services Installation Script
# This script installs and configures PostgreSQL and ArangoDB for the HADES project.
#

set -e  # Exit immediately if a command exits with a non-zero status

# Text formatting
BOLD="\033[1m"
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
RESET="\033[0m"

# Default configuration
POSTGRES_VERSION="15"
POSTGRES_USER="hades"
POSTGRES_PASSWORD="hades_password"
POSTGRES_DB="hades_auth"

# ArangoDB configuration
ARANGO_VERSION="3.11.5"
ARANGO_PACKAGE_VERSION="3.11.5-1"
ARANGO_USER="hades"
ARANGO_PASSWORD="hades_password"
ARANGO_DB="hades_graph"

# Detect architecture
ARCH=$(dpkg --print-architecture)
if [ "$ARCH" = "amd64" ]; then
    ARANGO_ARCH="amd64"
elif [ "$ARCH" = "arm64" ]; then
    ARANGO_ARCH="arm64"
else
    log "ERROR" "Unsupported architecture: $ARCH. Only amd64 and arm64 are supported."
    exit 1
fi

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Log file
LOG_FILE="$PROJECT_ROOT/install_services.log"

# Function to log messages
log() {
    local level=$1
    local message=$2
    local color=$RESET
    
    case $level in
        "INFO") color=$BLUE ;;
        "SUCCESS") color=$GREEN ;;
        "WARNING") color=$YELLOW ;;
        "ERROR") color=$RED ;;
    esac
    
    echo -e "${color}${BOLD}[$level]${RESET} $message"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" >> "$LOG_FILE"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a service is running
service_running() {
    systemctl is-active --quiet "$1"
}

# Function to install PostgreSQL
install_postgresql() {
    log "INFO" "Installing PostgreSQL $POSTGRES_VERSION..."
    
    if command_exists psql && service_running postgresql; then
        log "INFO" "PostgreSQL is already installed and running."
    else
        # Add PostgreSQL repository
        if [ ! -f /etc/apt/sources.list.d/pgdg.list ]; then
            log "INFO" "Adding PostgreSQL repository..."
            # Use the proper method for adding the key to avoid deprecation warnings
            wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg
            echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list > /dev/null
        fi
        
        # Install PostgreSQL
        log "INFO" "Updating package lists..."
        sudo apt-get update -qq
        
        log "INFO" "Installing PostgreSQL packages..."
        sudo apt-get install -y -qq postgresql-$POSTGRES_VERSION postgresql-contrib-$POSTGRES_VERSION
        
        # Start PostgreSQL service
        log "INFO" "Starting PostgreSQL service..."
        sudo systemctl enable postgresql
        sudo systemctl start postgresql
    fi
    
    # Check if PostgreSQL is running
    if service_running postgresql; then
        log "SUCCESS" "PostgreSQL installed and running successfully."
    else
        log "ERROR" "Failed to start PostgreSQL service."
        exit 1
    fi
}

# Function to configure PostgreSQL
configure_postgresql() {
    log "INFO" "Configuring PostgreSQL..."
    
    # Check if user already exists
    if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$POSTGRES_USER'" | grep -q 1; then
        log "INFO" "PostgreSQL user '$POSTGRES_USER' already exists."
    else
        # Create PostgreSQL user
        log "INFO" "Creating PostgreSQL user '$POSTGRES_USER'..."
        sudo -u postgres psql -c "CREATE USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';"
        sudo -u postgres psql -c "ALTER USER $POSTGRES_USER WITH SUPERUSER;"
    fi
    
    # Check if database already exists
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$POSTGRES_DB"; then
        log "INFO" "PostgreSQL database '$POSTGRES_DB' already exists."
    else
        # Create PostgreSQL database
        log "INFO" "Creating PostgreSQL database '$POSTGRES_DB'..."
        sudo -u postgres psql -c "CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER;"
    fi
    
    # Grant privileges
    log "INFO" "Granting privileges to '$POSTGRES_USER' on '$POSTGRES_DB'..."
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;"
    
    log "SUCCESS" "PostgreSQL configured successfully."
    
    # Display connection information
    log "INFO" "PostgreSQL connection information:"
    log "INFO" "  Host: localhost"
    log "INFO" "  Port: 5432"
    log "INFO" "  User: $POSTGRES_USER"
    log "INFO" "  Password: $POSTGRES_PASSWORD"
    log "INFO" "  Database: $POSTGRES_DB"
    log "INFO" "  Connection string: postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:5432/$POSTGRES_DB"
}

# Function to install ArangoDB
install_arangodb() {
    log "INFO" "Installing ArangoDB $ARANGO_VERSION..."
    
    if command_exists arangod && service_running arangodb3; then
        log "INFO" "ArangoDB is already installed and running."
    else
        # Remove any existing ArangoDB repository configuration to avoid conflicts
        if [ -f /etc/apt/sources.list.d/arangodb.list ]; then
            log "INFO" "Removing existing ArangoDB repository configuration..."
            sudo rm /etc/apt/sources.list.d/arangodb.list
        fi
        
        # Create temporary directory for downloads
        TEMP_DIR=$(mktemp -d)
        cd $TEMP_DIR
        
        # Download ArangoDB package directly
        log "INFO" "Downloading ArangoDB package for $ARANGO_ARCH architecture..."
        PACKAGE_URL="https://download.arangodb.com/arangodb311/Community/Linux/arangodb3_${ARANGO_PACKAGE_VERSION}_${ARANGO_ARCH}.deb"
        log "INFO" "Package URL: $PACKAGE_URL"
        
        if ! curl -fsSLO $PACKAGE_URL; then
            log "ERROR" "Failed to download ArangoDB package. Please check the URL and try again."
            cd - > /dev/null
            rm -rf $TEMP_DIR
            exit 1
        fi
        
        # Install dependencies
        log "INFO" "Installing dependencies..."
        sudo apt-get update -qq
        
        # Detect available library versions for Ubuntu Noble (24.04)
        log "INFO" "Detecting available library versions..."
        if apt-cache search libicu74 | grep -q libicu74; then
            log "INFO" "Found libicu74"
            ICU_LIB="libicu74"
        elif apt-cache search libicu72 | grep -q libicu72; then
            log "INFO" "Found libicu72"
            ICU_LIB="libicu72"
        else
            log "INFO" "Using default libicu"
            ICU_LIB="libicu-dev"
        fi
        
        if apt-cache search libssl3 | grep -q libssl3; then
            log "INFO" "Found libssl3"
            SSL_LIB="libssl3"
        else
            log "INFO" "Using default libssl"
            SSL_LIB="libssl-dev"
        fi
        
        log "INFO" "Installing $SSL_LIB and $ICU_LIB..."
        sudo apt-get install -y -qq $SSL_LIB $ICU_LIB
        
        # Set default password for non-interactive installation
        log "INFO" "Setting ArangoDB root password..."
        echo "arangodb3 arangodb3/password password $ARANGO_PASSWORD" | sudo debconf-set-selections
        echo "arangodb3 arangodb3/password_again password $ARANGO_PASSWORD" | sudo debconf-set-selections
        
        # Install ArangoDB package
        log "INFO" "Installing ArangoDB package..."
        sudo DEBIAN_FRONTEND=noninteractive dpkg -i arangodb3_${ARANGO_PACKAGE_VERSION}_${ARANGO_ARCH}.deb || true
        
        # Fix any dependency issues
        log "INFO" "Fixing dependencies..."
        sudo apt-get install -f -y -qq
        
        # Clean up
        cd - > /dev/null
        rm -rf $TEMP_DIR
        
        # Start ArangoDB service
        log "INFO" "Starting ArangoDB service..."
        sudo systemctl enable arangodb3
        sudo systemctl start arangodb3
        
        # Wait for ArangoDB to start (with timeout)
        log "INFO" "Waiting for ArangoDB to start (this may take a minute)..."
        TIMEOUT=60
        ELAPSED=0
        while [ $ELAPSED -lt $TIMEOUT ]; do
            if service_running arangodb3; then
                break
            fi
            sleep 5
            ELAPSED=$((ELAPSED + 5))
            log "INFO" "Still waiting for ArangoDB to start... ($ELAPSED seconds elapsed)"
        done
    fi
    
    # Check if ArangoDB is running
    if service_running arangodb3; then
        log "SUCCESS" "ArangoDB installed and running successfully."
    else
        log "ERROR" "Failed to start ArangoDB service."
        log "INFO" "Checking ArangoDB logs for errors..."
        sudo journalctl -u arangodb3 -n 20 --no-pager
        exit 1
    fi
}

# Function to configure ArangoDB
configure_arangodb() {
    log "INFO" "Configuring ArangoDB..."
    
    # Wait for ArangoDB to be fully started
    log "INFO" "Waiting for ArangoDB to be ready..."
    sleep 5
    
    # Create ArangoDB user and database
    log "INFO" "Creating ArangoDB user '$ARANGO_USER' and database '$ARANGO_DB'..."
    
    # Check if user already exists
    USER_EXISTS=$(arangosh --server.authentication=true --server.username=root --server.password="$ARANGO_PASSWORD" --javascript.execute-string "try { if (db._users.firstExample({user: '$ARANGO_USER'}) !== null) { print('true'); } else { print('false'); }} catch(e) { print('false'); }" 2>/dev/null || echo "false")
    
    if [ "$USER_EXISTS" = "true" ]; then
        log "INFO" "ArangoDB user '$ARANGO_USER' already exists."
    else
        # Create ArangoDB user
        log "INFO" "Creating new ArangoDB user '$ARANGO_USER'..."
        arangosh --server.authentication=true --server.username=root --server.password="$ARANGO_PASSWORD" --javascript.execute-string "try { require('@arangodb/users').save('$ARANGO_USER', '$ARANGO_PASSWORD'); } catch(e) { if (e.errorNum === 1702) { print('User already exists'); } else { throw e; }}" 2>/dev/null
    fi
    
    # Check if database already exists
    DB_EXISTS=$(arangosh --server.authentication=true --server.username=root --server.password="$ARANGO_PASSWORD" --javascript.execute-string "try { if (db._databases().includes('$ARANGO_DB')) { print('true'); } else { print('false'); }} catch(e) { print('false'); }" 2>/dev/null || echo "false")
    
    if [ "$DB_EXISTS" = "true" ]; then
        log "INFO" "ArangoDB database '$ARANGO_DB' already exists."
    else
        # Create ArangoDB database
        log "INFO" "Creating new ArangoDB database '$ARANGO_DB'..."
        arangosh --server.authentication=true --server.username=root --server.password="$ARANGO_PASSWORD" --javascript.execute-string "try { db._createDatabase('$ARANGO_DB'); } catch(e) { if (e.errorNum === 1207) { print('Database already exists'); } else { throw e; }}" 2>/dev/null
    fi
    
    # Grant permissions to user
    log "INFO" "Granting permissions to '$ARANGO_USER' on '$ARANGO_DB'..."
    arangosh --server.authentication=true --server.username=root --server.password="$ARANGO_PASSWORD" --javascript.execute-string "try { require('@arangodb/users').grantDatabase('$ARANGO_USER', '$ARANGO_DB', 'rw'); } catch(e) { console.log('Error granting permissions: ' + e.message); }" 2>/dev/null
    
    log "SUCCESS" "ArangoDB configured successfully."
    
    # Display connection information
    log "INFO" "ArangoDB connection information:"
    log "INFO" "  Host: localhost"
    log "INFO" "  Port: 8529"
    log "INFO" "  User: $ARANGO_USER"
    log "INFO" "  Password: $ARANGO_PASSWORD"
    log "INFO" "  Database: $ARANGO_DB"
    log "INFO" "  Web interface: http://localhost:8529"
}

# Function to create environment variables file
create_env_file() {
    local env_file="$PROJECT_ROOT/.env"
    
    log "INFO" "Creating environment variables file at $env_file..."
    
    if [ -f "$env_file" ]; then
        log "INFO" "Environment file already exists. Creating backup..."
        cp "$env_file" "${env_file}.backup.$(date +%Y%m%d%H%M%S)"
    fi
    
    cat > "$env_file" << EOF
# HADES Environment Variables
# Generated by install_services.sh on $(date)

# PostgreSQL Configuration
HADES_MCP__AUTH__DB_TYPE=postgresql
HADES_PG_HOST=localhost
HADES_PG_PORT=5432
HADES_PG_USER=$POSTGRES_USER
HADES_PG_PASSWORD=$POSTGRES_PASSWORD
HADES_PG_DATABASE=$POSTGRES_DB

# ArangoDB Configuration
HADES_ARANGO_HOST=localhost
HADES_ARANGO_PORT=8529
HADES_ARANGO_USER=$ARANGO_USER
HADES_ARANGO_PASSWORD=$ARANGO_PASSWORD
HADES_ARANGO_DATABASE=$ARANGO_DB
EOF
    
    log "SUCCESS" "Environment variables file created successfully."
    log "INFO" "To load these variables, run: source $env_file"
}

# Function to run tests
run_tests() {
    log "INFO" "Running database connection tests..."
    
    # Create test script
    local test_script="$PROJECT_ROOT/src/tools/test_db_connections.py"
    
    cat > "$test_script" << 'EOF'
#!/usr/bin/env python3
"""
Test database connections for HADES.
"""
import os
import sys
from datetime import datetime

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Error: psycopg2-binary package not installed.")
    print("Install it with: pip install psycopg2-binary")
    sys.exit(1)

try:
    from arango import ArangoClient
except ImportError:
    print("Error: python-arango package not installed.")
    print("Install it with: pip install python-arango")
    sys.exit(1)

def test_postgresql():
    """Test PostgreSQL connection."""
    print("\n--- Testing PostgreSQL Connection ---")
    
    host = os.environ.get("HADES_PG_HOST", "localhost")
    port = os.environ.get("HADES_PG_PORT", "5432")
    user = os.environ.get("HADES_PG_USER", "hades")
    password = os.environ.get("HADES_PG_PASSWORD", "hades_password")
    database = os.environ.get("HADES_PG_DATABASE", "hades_auth")
    
    print(f"Connecting to PostgreSQL at {host}:{port}, database: {database}, user: {user}")
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=database
        )
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"Connected successfully to PostgreSQL")
            print(f"PostgreSQL version: {version}")
            
            # Create test table
            print("Creating test table...")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS connection_test (
                id SERIAL PRIMARY KEY,
                message TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
            """)
            
            # Insert test data
            test_message = f"Connection test at {datetime.now().isoformat()}"
            cursor.execute(
                "INSERT INTO connection_test (message, created_at) VALUES (%s, %s) RETURNING id",
                (test_message, datetime.now())
            )
            test_id = cursor.fetchone()[0]
            
            # Retrieve test data
            cursor.execute("SELECT message FROM connection_test WHERE id = %s", (test_id,))
            retrieved_message = cursor.fetchone()[0]
            
            print(f"Test data written and retrieved successfully: '{retrieved_message}'")
            
            # Clean up
            cursor.execute("DROP TABLE connection_test")
            
        conn.commit()
        conn.close()
        print("PostgreSQL connection test completed successfully!")
        return True
    
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return False

def test_arangodb():
    """Test ArangoDB connection."""
    print("\n--- Testing ArangoDB Connection ---")
    
    host = os.environ.get("HADES_ARANGO_HOST", "localhost")
    port = os.environ.get("HADES_ARANGO_PORT", "8529")
    user = os.environ.get("HADES_ARANGO_USER", "hades")
    password = os.environ.get("HADES_ARANGO_PASSWORD", "hades_password")
    database = os.environ.get("HADES_ARANGO_DATABASE", "hades_graph")
    
    print(f"Connecting to ArangoDB at {host}:{port}, database: {database}, user: {user}")
    
    try:
        # Connect to ArangoDB
        client = ArangoClient(hosts=f"http://{host}:{port}")
        db = client.db(database, username=user, password=password)
        
        # Get version information
        version = db.version()
        print(f"Connected successfully to ArangoDB")
        print(f"ArangoDB version: {version}")
        
        # We're already connected to the database, so we can proceed with testing
        
        # Create test collection
        collection_name = "connection_test"
        if db.has_collection(collection_name):
            test_collection = db.collection(collection_name)
        else:
            test_collection = db.create_collection(collection_name)
        print(f"Using collection: {collection_name}")
        
        # Insert test document
        test_doc = {
            "message": f"Connection test at {datetime.now().isoformat()}",
            "created_at": datetime.now().isoformat()
        }
        meta = test_collection.insert(test_doc)
        doc_id = meta["_id"]
        
        # Retrieve test document
        retrieved_doc = test_collection.get(doc_id)
        print(f"Test document written and retrieved successfully: '{retrieved_doc['message']}'")
        
        # Clean up
        test_collection.delete(doc_id)
        db.delete_collection(collection_name)
        
        print("ArangoDB connection test completed successfully!")
        return True
    
    except Exception as e:
        print(f"Error connecting to ArangoDB: {e}")
        return False

def main():
    """Main function."""
    print("HADES Database Connection Tests")
    print("===============================")
    
    pg_success = test_postgresql()
    arango_success = test_arangodb()
    
    print("\n--- Test Summary ---")
    print(f"PostgreSQL: {'SUCCESS' if pg_success else 'FAILED'}")
    print(f"ArangoDB: {'SUCCESS' if arango_success else 'FAILED'}")
    
    if pg_success and arango_success:
        print("\nAll database connection tests passed successfully!")
        return 0
    else:
        print("\nSome database connection tests failed. Check the logs above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF
    
    chmod +x "$test_script"
    
    # Source environment variables
    source "$PROJECT_ROOT/.env"
    
    # Look for existing virtual environments
    log "INFO" "Looking for existing virtual environments..."
    
    # Check for virtual environments in common locations
    PARENT_VENV="$(dirname "$PROJECT_ROOT")/.venv"
    PROJECT_VENV="$PROJECT_ROOT/.venv"
    
    if [ -f "$PARENT_VENV/bin/python3" ] && [ -f "$PARENT_VENV/bin/pip" ]; then
        log "INFO" "Found existing virtual environment in parent directory."
        VENV_DIR="$PARENT_VENV"
    elif [ -f "$PROJECT_VENV/bin/python3" ] && [ -f "$PROJECT_VENV/bin/pip" ]; then
        log "INFO" "Found existing virtual environment in project directory."
        VENV_DIR="$PROJECT_VENV"
    else
        # No existing virtual environment found, create a new one
        log "INFO" "No existing virtual environment found. Creating a new one..."
        VENV_DIR="$PROJECT_ROOT/.venv"
        
        # Install required packages for virtual environment
        log "INFO" "Installing required packages for virtual environment..."
        sudo apt-get update -qq
        sudo apt-get install -y -qq python3-venv python3-pip python3-dev
        
        # Create virtual environment
        log "INFO" "Creating new virtual environment at $VENV_DIR..."
        python3 -m venv "$VENV_DIR" || python3 -m venv --system-site-packages "$VENV_DIR"
    fi
    
    # Verify virtual environment exists and is usable
    if [ ! -f "$VENV_DIR/bin/python3" ] || [ ! -f "$VENV_DIR/bin/pip" ]; then
        log "ERROR" "Virtual environment not properly created or found. Skipping Python package installation."
        log "INFO" "You can manually install the required packages with:"
        log "INFO" "  pip install psycopg2-binary python-arango"
        return 1
    fi
    
    log "INFO" "Using virtual environment at $VENV_DIR"
    
    # Activate virtual environment
    log "INFO" "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    
    # Install required Python packages
    log "INFO" "Installing required Python packages in virtual environment..."
    if [ -f "$VENV_DIR/bin/pip" ]; then
        "$VENV_DIR/bin/pip" install --upgrade pip || log "WARNING" "Failed to upgrade pip"
        log "INFO" "Installing psycopg2-binary and python-arango..."
        "$VENV_DIR/bin/pip" install psycopg2-binary python-arango || {
            log "WARNING" "Failed to install packages with pip. Trying with system packages..."
            sudo apt-get install -y -qq python3-psycopg2
            # python-arango is not available as a system package, so we'll skip the tests if we can't install it
        }
    else
        log "ERROR" "pip not found in virtual environment. Skipping Python package installation."
    fi
    
    # Run the test script using the Python interpreter from the virtual environment
    if [ -f "$VENV_DIR/bin/python3" ]; then
        log "INFO" "Running database connection tests..."
        "$VENV_DIR/bin/python3" "$test_script" || {
            log "WARNING" "Failed to run tests with virtual environment Python. Trying with system Python..."
            python3 "$test_script" || log "ERROR" "Failed to run database connection tests."
        }
        
        if [ $? -eq 0 ]; then
            log "SUCCESS" "Database connection tests completed successfully."
        else
            log "WARNING" "Some database connection tests failed. This is expected if python-arango is not installed."
            log "INFO" "You can manually install the required packages with:"
            log "INFO" "  source $VENV_DIR/bin/activate"
            log "INFO" "  pip install psycopg2-binary python-arango"
        fi
    else
        log "WARNING" "Python interpreter not found in virtual environment. Skipping database connection tests."
        log "INFO" "You can manually run the tests with:"
        log "INFO" "  python3 $test_script"
    fi
}

# Main function
main() {
    echo -e "${BOLD}${BLUE}HADES Services Installation${RESET}"
    echo -e "${BLUE}=============================${RESET}\n"
    
    # Check if running as root
    if [ "$(id -u)" -eq 0 ]; then
        log "ERROR" "This script should not be run as root. Please run as a regular user with sudo privileges."
        exit 1
    fi
    
    # Check for sudo privileges
    if ! sudo -v; then
        log "ERROR" "This script requires sudo privileges."
        exit 1
    fi
    
    # Create log file
    touch "$LOG_FILE"
    log "INFO" "Installation started. Log file: $LOG_FILE"
    
    # Install and configure PostgreSQL
    install_postgresql
    configure_postgresql
    
    # Install and configure ArangoDB
    install_arangodb
    configure_arangodb
    
    # Create environment variables file
    create_env_file
    
    # Run tests
    run_tests
    
    log "SUCCESS" "HADES services installation completed successfully!"
    log "INFO" "To start using the services, run: source $PROJECT_ROOT/.env"
}

# Run main function
main
