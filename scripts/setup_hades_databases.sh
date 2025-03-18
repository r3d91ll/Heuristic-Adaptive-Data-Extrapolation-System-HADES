#!/bin/bash
# HADES Database Setup Script
# This script sets up both PostgreSQL and ArangoDB for the HADES system
# It creates the necessary databases, users, and initializes the schema

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default configuration
POSTGRES_USER="hades"
POSTGRES_DB="hades_test"
POSTGRES_PASSWORD="o\$n^3W%QD0HGWxH!"
ARANGO_USER="hades"
ARANGO_DB="hades_graph"
ARANGO_PASSWORD="dpvL#tocbHQeKBd4"
ARANGO_HOST="http://localhost:8529"

# Get script directory
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

# Function to print section headers
print_section() {
    echo -e "\n${YELLOW}=== $1 ===${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Function to read values from .env file if it exists
read_env_file() {
    if [ -f "$ENV_FILE" ]; then
        echo -e "${GREEN}Reading configuration from $ENV_FILE${NC}"
        
        # Source the .env file if it exists
        set -a
        [ -f "$ENV_FILE" ] && . "$ENV_FILE"
        set +a
        
        # Override variables if they exist in .env
        [ ! -z "${HADES_PG_USER}" ] && POSTGRES_USER="${HADES_PG_USER}"
        [ ! -z "${HADES_PG_PASSWORD}" ] && POSTGRES_PASSWORD="${HADES_PG_PASSWORD}"
        [ ! -z "${HADES_PG_DATABASE}" ] && POSTGRES_DB="${HADES_PG_DATABASE}"
        [ ! -z "${HADES_ARANGO_USER}" ] && ARANGO_USER="${HADES_ARANGO_USER}"
        [ ! -z "${HADES_ARANGO_PASSWORD}" ] && ARANGO_PASSWORD="${HADES_ARANGO_PASSWORD}"
        [ ! -z "${HADES_ARANGO_DATABASE}" ] && ARANGO_DB="${HADES_ARANGO_DATABASE}"
        [ ! -z "${HADES_ARANGO_HOST}" ] && ARANGO_HOST="${HADES_ARANGO_HOST}"
    else
        echo -e "${YELLOW}No .env file found. Using default configuration.${NC}"
        
        # Create .env file with default values
        cat > "$ENV_FILE" << EOF
# PostgreSQL Configuration
HADES_PG_USER=$POSTGRES_USER
HADES_PG_PASSWORD=$POSTGRES_PASSWORD
HADES_PG_DATABASE=$POSTGRES_DB
HADES_PG_HOST=localhost
HADES_PG_PORT=5432

# ArangoDB Configuration
HADES_ARANGO_HOST=$ARANGO_HOST
HADES_ARANGO_USER=$ARANGO_USER
HADES_ARANGO_PASSWORD=$ARANGO_PASSWORD
HADES_ARANGO_DATABASE=$ARANGO_DB
EOF
        echo -e "${GREEN}Created .env file with default configuration at $ENV_FILE${NC}"
    fi
}

# Function to setup PostgreSQL
setup_postgresql() {
    print_section "PostgreSQL Setup"
    
    # Check if PostgreSQL is installed
    if ! command_exists psql; then
        echo -e "${RED}PostgreSQL is not installed. Please install PostgreSQL first.${NC}"
        echo -e "For Ubuntu: sudo apt install postgresql postgresql-contrib"
        return 1
    fi
    
    # Check if PostgreSQL service is running
    if ! systemctl is-active --quiet postgresql; then
        echo -e "${YELLOW}PostgreSQL is not running. Starting PostgreSQL...${NC}"
        sudo systemctl start postgresql
    fi
    
    echo -e "${GREEN}PostgreSQL is running.${NC}"
    
    # Create PostgreSQL user if it doesn't exist
    echo -e "${YELLOW}Creating PostgreSQL user '$POSTGRES_USER' if it doesn't exist...${NC}"
    sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$POSTGRES_USER'" | grep -q 1 || \
        sudo -u postgres psql -c "CREATE USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';"
    
    # Create PostgreSQL database if it doesn't exist
    echo -e "${YELLOW}Creating PostgreSQL database '$POSTGRES_DB' if it doesn't exist...${NC}"
    sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$POSTGRES_DB'" | grep -q 1 || \
        sudo -u postgres psql -c "CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER;"
    
    # Grant privileges
    echo -e "${YELLOW}Granting privileges on database '$POSTGRES_DB' to user '$POSTGRES_USER'...${NC}"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;"
    
    # Create .pgpass file for passwordless authentication during tests
    PGPASS_FILE="$HOME/.pgpass"
    echo -e "${YELLOW}Creating .pgpass file for passwordless authentication...${NC}"
    echo "localhost:5432:$POSTGRES_DB:$POSTGRES_USER:$POSTGRES_PASSWORD" > "$PGPASS_FILE"
    chmod 600 "$PGPASS_FILE"
    
    echo -e "${GREEN}PostgreSQL setup completed successfully.${NC}"
    
    # Initialize the database schema
    echo -e "${YELLOW}Initializing PostgreSQL schema...${NC}"
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    # Create the api_keys table if it doesn't exist
    psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
    CREATE TABLE IF NOT EXISTS api_keys (
        key_id VARCHAR(255) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        key_hash VARCHAR(255) NOT NULL UNIQUE,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP WITH TIME ZONE,
        is_active BOOLEAN NOT NULL DEFAULT TRUE
    );
    
    CREATE TABLE IF NOT EXISTS rate_limits (
        key_id VARCHAR(255) NOT NULL REFERENCES api_keys(key_id),
        timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (key_id, timestamp)
    );
    "
    
    echo -e "${GREEN}PostgreSQL schema initialized successfully.${NC}"
}

# Function to setup ArangoDB
setup_arangodb() {
    print_section "ArangoDB Setup"
    
    # Check if ArangoDB is installed
    if ! command_exists arangod && ! command_exists arangosh; then
        echo -e "${RED}ArangoDB is not installed. Please install ArangoDB first.${NC}"
        echo -e "${YELLOW}For Ubuntu: Check installation instructions at https://www.arangodb.com/docs/stable/installation-linux-ubuntu.html${NC}"
        echo -e "${YELLOW}You may need to build from source for Noble (24.04): https://github.com/arangodb/arangodb${NC}"
        return 1
    else
        echo -e "${GREEN}ArangoDB is installed.${NC}"
        
        # Check if ArangoDB service is running
        if ! systemctl is-active --quiet arangodb3; then
            echo -e "${YELLOW}ArangoDB is not running. Starting ArangoDB...${NC}"
            sudo systemctl start arangodb3
            sleep 5 # Give it time to start
        fi
        
        echo -e "${GREEN}ArangoDB service is running.${NC}"
        
        # Prompt for root password
        echo -e "${YELLOW}Please enter the ArangoDB root password:${NC}"
        read -s ARANGO_ROOT_PASSWORD
        echo
    fi
    
    # Create JavaScript file for ArangoDB setup
    JS_SCRIPT="$SCRIPT_DIR/temp_setup_arango.js"
    
    cat > "$JS_SCRIPT" << EOF
// ArangoDB setup script
const dbName = '${ARANGO_DB}';
const username = '${ARANGO_USER}';
const password = '${ARANGO_PASSWORD}';

// Check if database exists, create if not
try {
  if (!db._databases().includes(dbName)) {
    console.log(\`Creating database \${dbName}...\`);
    db._createDatabase(dbName);
    console.log(\`Database \${dbName} created successfully.\`);
  } else {
    console.log(\`Database \${dbName} already exists.\`);
  }
} catch (e) {
  console.error(\`Error creating database: \${e.message}\`);
  process.exit(1);
}

// Check if user exists, create if not
try {
  const users = require('@arangodb/users');
  if (!users.exists(username)) {
    console.log(\`Creating user \${username}...\`);
    users.save(username, password);
    console.log(\`User \${username} created successfully.\`);
  } else {
    console.log(\`User \${username} already exists.\`);
    // Update password
    users.update(username, password);
    console.log(\`Updated password for user \${username}.\`);
  }
  
  // Grant access to the database
  users.grantDatabase(username, dbName, 'rw');
  console.log(\`Granted access to database \${dbName} for user \${username}.\`);
} catch (e) {
  console.error(\`Error managing user: \${e.message}\`);
  process.exit(1);
}

// Switch to the database to create collections
try {
  db._useDatabase(dbName);
  
  // Create collections if they don't exist
  const collections = [
    'entities', 'relationships', 'change_logs', 'metadata',
    'facts', 'sources', 'embeddings', 'versions'
  ];
  
  collections.forEach(collName => {
    if (!db._collection(collName)) {
      console.log(\`Creating collection \${collName}...\`);
      db._createDocumentCollection(collName);
      console.log(\`Collection \${collName} created successfully.\`);
    } else {
      console.log(\`Collection \${collName} already exists.\`);
    }
  });
  
  // Create edge collections if they don't exist
  const edgeCollections = [
    'entity_relationships', 'entity_facts', 'fact_sources'
  ];
  
  edgeCollections.forEach(collName => {
    if (!db._collection(collName)) {
      console.log(\`Creating edge collection \${collName}...\`);
      db._createEdgeCollection(collName);
      console.log(\`Edge collection \${collName} created successfully.\`);
    } else {
      console.log(\`Edge collection \${collName} already exists.\`);
    }
  });
  
  // Create indexes
  console.log('Creating indexes...');
  
  // Entity indexes
  if (db.entities) {
    if (!db.entities.indexes().some(idx => idx.type === 'hash' && idx.fields.includes('entity_id'))) {
      db.entities.ensureIndex({ type: 'hash', fields: ['entity_id'], unique: true });
      console.log('Created hash index on entities.entity_id');
    }
  }
  
  // Relationship indexes
  if (db.relationships) {
    if (!db.relationships.indexes().some(idx => idx.type === 'hash' && idx.fields.includes('relationship_id'))) {
      db.relationships.ensureIndex({ type: 'hash', fields: ['relationship_id'], unique: true });
      console.log('Created hash index on relationships.relationship_id');
    }
  }
  
  // Add a test entry to change_logs if it's empty
  if (db.change_logs && db.change_logs.count() === 0) {
    console.log('Adding test entry to change_logs...');
    db.change_logs.save({
      entity_id: 'test/entity',
      previous_version: null,
      new_version: 'v0.1.0',
      commit_id: require('crypto').createHash('sha256').update(Date.now().toString()).digest('hex'),
      timestamp: new Date().toISOString(),
      changes: {
        added: { name: 'Test Entity' },
        removed: {},
        modified: {}
      },
      commit_message: 'Initial test entry for change_logs'
    });
    console.log('Test entry added to change_logs.');
  }
  
  console.log('ArangoDB setup completed successfully.');
} catch (e) {
  console.error(\`Error setting up database: \${e.message}\`);
  process.exit(1);
}
EOF
    
    # Execute the JavaScript file with arangosh
    echo -e "${YELLOW}Setting up ArangoDB database and user...${NC}"
    arangosh \
      --server.endpoint tcp://127.0.0.1:8529 \
      --server.username root \
      --server.password "$ARANGO_ROOT_PASSWORD" \
      --javascript.execute "$JS_SCRIPT"
    
    # Clean up temporary file
    rm "$JS_SCRIPT"
    
    # Verify access with the new user
    echo -e "${YELLOW}Verifying $ARANGO_USER user access to $ARANGO_DB...${NC}"
    if arangosh \
      --server.endpoint tcp://127.0.0.1:8529 \
      --server.username "$ARANGO_USER" \
      --server.password "$ARANGO_PASSWORD" \
      --server.database "$ARANGO_DB" \
      --javascript.execute-string "print('Connection successful');" &> /dev/null; then
      echo -e "${GREEN}ArangoDB setup completed successfully.${NC}"
    else
      echo -e "${RED}Failed to verify ArangoDB user access. Please check your credentials.${NC}"
      return 1
    fi
}

# Function to run Python database initialization
run_python_init() {
    print_section "Python Database Initialization"
    
    # Check if Python is installed
    if ! command_exists python3; then
        echo -e "${RED}Python 3 is not installed. Please install Python 3 first.${NC}"
        return 1
    fi
    
    # Check if virtual environment exists
    VENV_DIR="$PROJECT_ROOT/.venv"
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}Virtual environment not found. Creating one...${NC}"
        python3 -m venv "$VENV_DIR"
        echo -e "${GREEN}Virtual environment created at $VENV_DIR${NC}"
    fi
    
    # Activate virtual environment
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source "$VENV_DIR/bin/activate"
    
    # Install required packages
    echo -e "${YELLOW}Installing required packages...${NC}"
    pip install -q -r "$PROJECT_ROOT/requirements.txt"
    
    # Run the Python database initialization script
    echo -e "${YELLOW}Running Python database initialization...${NC}"
    cd "$PROJECT_ROOT"
    python -m src.db.database_setup
    
    # Deactivate virtual environment
    deactivate
    
    echo -e "${GREEN}Python database initialization completed successfully.${NC}"
}

# Main function
main() {
    print_section "HADES Database Setup"
    
    # Read configuration from .env file
    read_env_file
    
    # Setup PostgreSQL
    setup_postgresql || { echo -e "${RED}PostgreSQL setup failed.${NC}"; exit 1; }
    
    # Setup ArangoDB
    setup_arangodb || { echo -e "${RED}ArangoDB setup failed.${NC}"; exit 1; }
    
    # Run Python initialization
    run_python_init || { echo -e "${RED}Python initialization failed.${NC}"; exit 1; }
    
    print_section "Setup Complete"
    echo -e "${GREEN}HADES database setup completed successfully.${NC}"
    echo -e "${GREEN}PostgreSQL database: $POSTGRES_DB${NC}"
    echo -e "${GREEN}ArangoDB database: $ARANGO_DB${NC}"
    echo -e "\n${YELLOW}You can now start using the HADES system.${NC}"
}

# Run the main function
main
