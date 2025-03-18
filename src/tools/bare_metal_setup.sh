#!/bin/bash
#
# HADES Bare Metal Environment Setup
# This script sets up a native environment with:
# - Local PostgreSQL (already installed)
# - Native ArangoDB installation
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
POSTGRES_USER="hades"
POSTGRES_PASSWORD="hades_password"
POSTGRES_DB="hades_auth"
POSTGRES_PORT="5432"

ARANGO_USER="hades"
ARANGO_PASSWORD="hades_password"
ARANGO_DB="hades_graph"
ARANGO_PORT="8529"
ARANGO_VERSION="3.9"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Log file
LOG_FILE="$PROJECT_ROOT/hybrid_setup.log"

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

# Function to check ArangoDB installation
check_arangodb() {
    log "INFO" "Checking ArangoDB installation..."
    
    if ! command_exists arangod; then
        log "ERROR" "ArangoDB is not installed. Please install ArangoDB first."
        log "INFO" "Visit https://www.arangodb.com/download-major/ for installation instructions."
        exit 1
    fi
    
    # Check if ArangoDB service is running
    if ! systemctl is-active --quiet arangodb3; then
        log "WARNING" "ArangoDB service is not running. Attempting to start it..."
        sudo systemctl start arangodb3
        
        if ! systemctl is-active --quiet arangodb3; then
            log "ERROR" "Failed to start ArangoDB service."
            exit 1
        fi
    fi
    
    log "SUCCESS" "ArangoDB is installed and running."
}

# Function to configure PostgreSQL
configure_postgresql() {
    log "INFO" "Configuring PostgreSQL..."
    
    # Check if PostgreSQL is running
    if ! pg_isready -q; then
        log "ERROR" "PostgreSQL is not running. Please start PostgreSQL service."
        exit 1
    fi
    
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

# Function to setup native ArangoDB
setup_arango_native() {
    log "INFO" "Setting up ArangoDB natively..."
    
    # Check if ArangoDB is running
    if ! curl -s http://localhost:$ARANGO_PORT/_api/version > /dev/null; then
        log "WARNING" "ArangoDB is not responding. Attempting to start the service..."
        sudo systemctl start arangodb3
        sleep 5
        
        if ! curl -s http://localhost:$ARANGO_PORT/_api/version > /dev/null; then
            log "ERROR" "ArangoDB is still not responding after starting the service."
            exit 1
        fi
    fi
    
    log "SUCCESS" "ArangoDB service is running."
    
    # Configure ArangoDB
    log "INFO" "Configuring ArangoDB..."
    
    # Create ArangoDB user and database using arangosh
    arangosh \
        --server.authentication=true \
        --server.username=root \
        --server.password="$ARANGO_PASSWORD" \
        --javascript.execute-string "
            // Create user if not exists
            try {
                require('@arangodb/users').save('$ARANGO_USER', '$ARANGO_PASSWORD');
                print('User $ARANGO_USER created');
            } catch (e) {
                if (e.errorNum === 1702) {
                    print('User $ARANGO_USER already exists');
                } else {
                    throw e;
                }
            }
            
            // Create database if not exists
            if (!db._databases().includes('$ARANGO_DB')) {
                db._createDatabase('$ARANGO_DB');
                print('Database $ARANGO_DB created');
            } else {
                print('Database $ARANGO_DB already exists');
            }
            
            // Grant permissions
            require('@arangodb/users').grantDatabase('$ARANGO_USER', '$ARANGO_DB', 'rw');
            print('Permissions granted to $ARANGO_USER on $ARANGO_DB');
        "
    
    log "SUCCESS" "ArangoDB configured successfully."
    
    # Display connection information
    log "INFO" "ArangoDB connection information:"
    log "INFO" "  Host: localhost"
    log "INFO" "  Port: $ARANGO_PORT"
    log "INFO" "  User: $ARANGO_USER"
    log "INFO" "  Password: $ARANGO_PASSWORD"
    log "INFO" "  Database: $ARANGO_DB"
    log "INFO" "  Web interface: http://localhost:$ARANGO_PORT"
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
# Generated by bare_metal_setup.sh on $(date)

# PostgreSQL Configuration
HADES_MCP__AUTH__DB_TYPE=postgresql
HADES_PG_HOST=localhost
HADES_PG_PORT=$POSTGRES_PORT
HADES_PG_USER=$POSTGRES_USER
HADES_PG_PASSWORD=$POSTGRES_PASSWORD
HADES_PG_DATABASE=$POSTGRES_DB

# ArangoDB Configuration
HADES_ARANGO_HOST=localhost
HADES_ARANGO_PORT=$ARANGO_PORT
HADES_ARANGO_USER=$ARANGO_USER
HADES_ARANGO_PASSWORD=$ARANGO_PASSWORD
HADES_ARANGO_DATABASE=$ARANGO_DB
EOF
    
    log "SUCCESS" "Environment variables file created successfully."
    log "INFO" "To load these variables, run: source $env_file"
}

# Function to create test script
create_test_script() {
    local test_script="$PROJECT_ROOT/src/tools/test_hybrid_connections.py"
    
    log "INFO" "Creating database connection test script at $test_script..."
    
    cat > "$test_script" << 'EOF'
#!/usr/bin/env python3
"""
Test database connections for HADES hybrid environment.
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
        client = ArangoClient(hosts=f"http://{host}:{port}")
        
        # Connect to system database to verify credentials
        sys_db = client.db("_system", username=user, password=password)
        version = sys_db.version()
        print(f"Connected successfully to ArangoDB")
        print(f"ArangoDB version: {version}")
        
        # Check if test database exists, create if not
        if not sys_db.has_database(database):
            sys_db.create_database(database)
            print(f"Created database: {database}")
        
        # Connect to the test database
        db = client.db(database, username=user, password=password)
        
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
    print("HADES Hybrid Database Connection Tests")
    print("=====================================")
    
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
    
    log "SUCCESS" "Database connection test script created successfully."
}

# Function to run tests
run_tests() {
    log "INFO" "Running database connection tests..."
    
    # Source environment variables
    source "$PROJECT_ROOT/.env"
    
    # Run the test script
    python3 "$PROJECT_ROOT/src/tools/test_native_connections.py"
    
    if [ $? -eq 0 ]; then
        log "SUCCESS" "Database connection tests completed successfully."
    else
        log "ERROR" "Some database connection tests failed."
    fi
}

# Main function
main() {
    echo -e "${BOLD}${BLUE}HADES Bare Metal Environment Setup${RESET}"
    echo -e "${BLUE}====================================${RESET}\n"
    
    # Create log file
    touch "$LOG_FILE"
    log "INFO" "Bare metal environment setup started. Log file: $LOG_FILE"
    
    # Check ArangoDB installation
    check_arangodb
    
    # Configure PostgreSQL
    configure_postgresql
    
    # Setup native ArangoDB
    setup_arango_native
    
    # Create environment variables file
    create_env_file
    
    # Create test script
    create_test_script
    
    # Run tests
    run_tests
    
    log "SUCCESS" "HADES bare metal environment setup completed successfully!"
    log "INFO" "To start using the services, run: source $PROJECT_ROOT/.env"
    log "INFO" "To manage ArangoDB service, use: sudo systemctl {start|stop|restart} arangodb3"
    log "INFO" "To check ArangoDB status, use: sudo systemctl status arangodb3"
}

# Run main function
main
