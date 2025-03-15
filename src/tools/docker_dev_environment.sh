#!/bin/bash
#
# HADES Docker Development Environment Setup
# This script sets up a Docker-based development environment with PostgreSQL and ArangoDB.
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

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Docker compose file
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

# Log file
LOG_FILE="$PROJECT_ROOT/docker_dev_environment.log"

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

# Function to check Docker installation
check_docker() {
    log "INFO" "Checking Docker installation..."
    
    if ! command_exists docker; then
        log "ERROR" "Docker is not installed. Please install Docker first."
        log "INFO" "Visit https://docs.docker.com/get-docker/ for installation instructions."
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        log "ERROR" "Docker Compose is not installed. Please install Docker Compose first."
        log "INFO" "Visit https://docs.docker.com/compose/install/ for installation instructions."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        log "ERROR" "Docker daemon is not running. Please start Docker daemon first."
        exit 1
    fi
    
    log "SUCCESS" "Docker and Docker Compose are installed and running."
}

# Function to create Docker Compose file
create_docker_compose_file() {
    log "INFO" "Creating Docker Compose file at $DOCKER_COMPOSE_FILE..."
    
    cat > "$DOCKER_COMPOSE_FILE" << EOF
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: hades_postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "${POSTGRES_PORT}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  arangodb:
    image: arangodb:3.9
    container_name: hades_arangodb
    environment:
      ARANGO_ROOT_PASSWORD: ${ARANGO_PASSWORD}
    ports:
      - "${ARANGO_PORT}:8529"
    volumes:
      - arango_data:/var/lib/arangodb3
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8529/_api/version"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  arango_data:
EOF
    
    log "SUCCESS" "Docker Compose file created successfully."
}

# Function to start Docker containers
start_containers() {
    log "INFO" "Starting Docker containers..."
    
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    log "INFO" "Waiting for containers to be ready..."
    sleep 10
    
    # Check if containers are running
    if docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "hades_postgres" && \
       docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "hades_arangodb"; then
        log "SUCCESS" "Docker containers started successfully."
    else
        log "ERROR" "Failed to start Docker containers."
        exit 1
    fi
}

# Function to configure ArangoDB
configure_arangodb() {
    log "INFO" "Configuring ArangoDB..."
    
    # Create ArangoDB user and database
    log "INFO" "Creating ArangoDB user '$ARANGO_USER' and database '$ARANGO_DB'..."
    
    # Execute ArangoDB setup commands
    docker exec -it hades_arangodb arangosh \
        --server.authentication=true \
        --server.username=root \
        --server.password="$ARANGO_PASSWORD" \
        --javascript.execute-string "
            // Create user if not exists
            if (require('@arangodb/users').document('$ARANGO_USER') === null) {
                require('@arangodb/users').save('$ARANGO_USER', '$ARANGO_PASSWORD');
                print('User $ARANGO_USER created');
            } else {
                print('User $ARANGO_USER already exists');
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
}

# Function to create environment variables file
create_env_file() {
    local env_file="$PROJECT_ROOT/.env.docker"
    
    log "INFO" "Creating environment variables file at $env_file..."
    
    if [ -f "$env_file" ]; then
        log "INFO" "Environment file already exists. Creating backup..."
        cp "$env_file" "${env_file}.backup.$(date +%Y%m%d%H%M%S)"
    fi
    
    cat > "$env_file" << EOF
# HADES Docker Environment Variables
# Generated by docker_dev_environment.sh on $(date)

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
    local test_script="$PROJECT_ROOT/src/tools/test_docker_connections.py"
    
    log "INFO" "Creating database connection test script at $test_script..."
    
    cat > "$test_script" << 'EOF'
#!/usr/bin/env python3
"""
Test database connections for HADES Docker environment.
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
    print("HADES Docker Database Connection Tests")
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

# Function to display help information
show_help() {
    local script_name=$(basename "$0")
    
    echo -e "${BOLD}${BLUE}HADES Docker Development Environment Setup${RESET}"
    echo -e "${BLUE}=========================================${RESET}\n"
    
    echo -e "Usage: ${BOLD}$script_name [OPTIONS]${RESET}\n"
    
    echo -e "Options:"
    echo -e "  ${BOLD}-h, --help${RESET}              Show this help message and exit"
    echo -e "  ${BOLD}-s, --start${RESET}             Start the Docker containers"
    echo -e "  ${BOLD}-t, --test${RESET}              Run database connection tests"
    echo -e "  ${BOLD}-d, --down${RESET}              Stop and remove the Docker containers"
    echo -e "  ${BOLD}--postgres-user USER${RESET}    Set PostgreSQL username (default: $POSTGRES_USER)"
    echo -e "  ${BOLD}--postgres-pass PASS${RESET}    Set PostgreSQL password (default: $POSTGRES_PASSWORD)"
    echo -e "  ${BOLD}--postgres-db DB${RESET}        Set PostgreSQL database name (default: $POSTGRES_DB)"
    echo -e "  ${BOLD}--postgres-port PORT${RESET}    Set PostgreSQL port (default: $POSTGRES_PORT)"
    echo -e "  ${BOLD}--arango-user USER${RESET}      Set ArangoDB username (default: $ARANGO_USER)"
    echo -e "  ${BOLD}--arango-pass PASS${RESET}      Set ArangoDB password (default: $ARANGO_PASSWORD)"
    echo -e "  ${BOLD}--arango-db DB${RESET}          Set ArangoDB database name (default: $ARANGO_DB)"
    echo -e "  ${BOLD}--arango-port PORT${RESET}      Set ArangoDB port (default: $ARANGO_PORT)"
    echo -e "\n"
    
    echo -e "Examples:"
    echo -e "  ${BOLD}$script_name${RESET}                    Setup with default settings"
    echo -e "  ${BOLD}$script_name --start${RESET}            Start the Docker containers"
    echo -e "  ${BOLD}$script_name --test${RESET}             Run database connection tests"
    echo -e "  ${BOLD}$script_name --down${RESET}             Stop and remove the Docker containers"
    echo -e "  ${BOLD}$script_name --postgres-pass secure123 --arango-pass secure456${RESET}    Setup with custom passwords"
}

# Function to run tests
run_tests() {
    log "INFO" "Running database connection tests..."
    
    # Source environment variables
    source "$PROJECT_ROOT/.env.docker"
    
    # Run the test script
    python3 "$PROJECT_ROOT/src/tools/test_docker_connections.py"
    
    if [ $? -eq 0 ]; then
        log "SUCCESS" "Database connection tests completed successfully."
    else
        log "ERROR" "Some database connection tests failed."
    fi
}

# Function to stop and remove Docker containers
stop_containers() {
    log "INFO" "Stopping and removing Docker containers..."
    
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    
    log "SUCCESS" "Docker containers stopped and removed successfully."
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -s|--start)
                START_CONTAINERS=true
                shift
                ;;
            -t|--test)
                RUN_TESTS=true
                shift
                ;;
            -d|--down)
                STOP_CONTAINERS=true
                shift
                ;;
            --postgres-user)
                POSTGRES_USER="$2"
                shift 2
                ;;
            --postgres-pass)
                POSTGRES_PASSWORD="$2"
                shift 2
                ;;
            --postgres-db)
                POSTGRES_DB="$2"
                shift 2
                ;;
            --postgres-port)
                POSTGRES_PORT="$2"
                shift 2
                ;;
            --arango-user)
                ARANGO_USER="$2"
                shift 2
                ;;
            --arango-pass)
                ARANGO_PASSWORD="$2"
                shift 2
                ;;
            --arango-db)
                ARANGO_DB="$2"
                shift 2
                ;;
            --arango-port)
                ARANGO_PORT="$2"
                shift 2
                ;;
            *)
                log "ERROR" "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Main function
main() {
    # Parse command line arguments
    parse_args "$@"
    
    # Create log file
    touch "$LOG_FILE"
    log "INFO" "Docker development environment setup started. Log file: $LOG_FILE"
    
    # Check Docker installation
    check_docker
    
    # Handle specific actions
    if [ "$STOP_CONTAINERS" = true ]; then
        stop_containers
        exit 0
    fi
    
    if [ "$RUN_TESTS" = true ]; then
        run_tests
        exit 0
    fi
    
    # Create Docker Compose file
    create_docker_compose_file
    
    # Create test script
    create_test_script
    
    # Create environment variables file
    create_env_file
    
    # Start containers if requested or by default
    if [ "$START_CONTAINERS" = true ] || [ -z "$START_CONTAINERS" ]; then
        start_containers
        
        # Configure ArangoDB
        configure_arangodb
        
        # Run tests
        run_tests
    fi
    
    log "SUCCESS" "HADES Docker development environment setup completed successfully!"
    log "INFO" "To start using the services, run: source $PROJECT_ROOT/.env.docker"
    log "INFO" "To stop the containers, run: $0 --down"
}

# Run main function with all arguments
main "$@"
