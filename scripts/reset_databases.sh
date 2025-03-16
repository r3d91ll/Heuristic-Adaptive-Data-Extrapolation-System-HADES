#!/bin/bash
# Database Reset Script for HADES
# This script safely wipes both PostgreSQL and ArangoDB databases used by HADES
# It requires confirmation to proceed, as it will DELETE ALL DATA
#
# Usage: ./reset_databases.sh [--force]
# --force: Skip confirmation (use with caution, typically only in CI environments)

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_DIR="$(dirname "$(dirname "$(realpath "$0")")")"
echo "Project directory: $PROJECT_DIR"

# Import environment variables if .env exists
ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
  echo -e "${GREEN}Loading environment from .env file...${NC}"
  source "$ENV_FILE"
else
  echo -e "${RED}Error: .env file not found at $ENV_FILE${NC}"
  echo "Please make sure the .env file exists with the proper database configuration."
  exit 1
fi

# Database names from environment
PG_DATABASE="${HADES_PG_DATABASE:-hades_test}"
ARANGO_DATABASE="${HADES_ARANGO_DATABASE:-hades_graph}"

# Database user from environment
DB_USER="${HADES_PG_USER:-hades}"

# Skip confirmation if --force is passed
SKIP_CONFIRMATION=0
if [ "$1" == "--force" ]; then
  SKIP_CONFIRMATION=1
  echo -e "${YELLOW}Force flag detected. Skipping confirmation.${NC}"
fi

# Function to confirm deletion
confirm_deletion() {
  if [ $SKIP_CONFIRMATION -eq 1 ]; then
    return 0
  fi
  
  echo -e "${RED}WARNING: This will DELETE ALL DATA in the following databases:${NC}"
  echo -e "  - PostgreSQL: ${YELLOW}$PG_DATABASE${NC}"
  echo -e "  - ArangoDB: ${YELLOW}$ARANGO_DATABASE${NC}"
  echo
  echo -e "${RED}This action cannot be undone!${NC}"
  echo
  read -p "Type 'DELETE' to confirm: " confirmation
  
  if [ "$confirmation" != "DELETE" ]; then
    echo -e "${YELLOW}Aborted. No changes were made.${NC}"
    return 1
  fi
  
  return 0
}

# Function to reset PostgreSQL database
reset_postgresql() {
  echo -e "${GREEN}[1/2] Resetting PostgreSQL database...${NC}"
  
  # Check if PostgreSQL is running
  if ! systemctl is-active --quiet postgresql; then
    echo -e "  ${RED}✗${NC} PostgreSQL is not running. Cannot reset database."
    return 1
  fi
  
  # Drop and recreate the database
  echo -e "  ${YELLOW}•${NC} Dropping database $PG_DATABASE..."
  PGPASSWORD="$HADES_PG_PASSWORD" dropdb -U "$DB_USER" --if-exists "$PG_DATABASE"
  
  echo -e "  ${YELLOW}•${NC} Creating database $PG_DATABASE..."
  PGPASSWORD="$HADES_PG_PASSWORD" createdb -U "$DB_USER" "$PG_DATABASE"
  
  # Run init schema if available
  SCHEMA_FILE="$PROJECT_DIR/schemas/postgresql_init.sql"
  if [ -f "$SCHEMA_FILE" ]; then
    echo -e "  ${YELLOW}•${NC} Initializing schema from $SCHEMA_FILE..."
    PGPASSWORD="$HADES_PG_PASSWORD" psql -U "$DB_USER" -d "$PG_DATABASE" -f "$SCHEMA_FILE"
  else
    echo -e "  ${YELLOW}!${NC} Warning: Schema file not found at $SCHEMA_FILE"
    echo -e "  ${YELLOW}!${NC} Database created but schema not initialized."
  fi
  
  echo -e "  ${GREEN}✓${NC} PostgreSQL database reset successfully."
  return 0
}

# Function to reset ArangoDB database
reset_arangodb() {
  echo -e "${GREEN}[2/2] Resetting ArangoDB database...${NC}"
  
  # Check if ArangoDB is running
  if ! curl -s http://localhost:8529/_api/version > /dev/null; then
    echo -e "  ${RED}✗${NC} Cannot connect to ArangoDB at http://localhost:8529. Check if it's running."
    return 1
  fi
  
  # Create a temporary JavaScript file for ArangoDB
  TMP_JS_FILE=$(mktemp)
  cat > "$TMP_JS_FILE" <<EOF
  try {
    // Check if database exists
    const dbExists = db._databases().includes('$ARANGO_DATABASE');
    
    if (dbExists) {
      // Drop the database
      require('@arangodb/replication').stopReplicationClient('$ARANGO_DATABASE');
      db._dropDatabase('$ARANGO_DATABASE');
      print('Dropped database $ARANGO_DATABASE');
    }
    
    // Create a new database
    db._createDatabase('$ARANGO_DATABASE');
    print('Created database $ARANGO_DATABASE');
    
    // Switch to the new database and create collections
    db._useDatabase('$ARANGO_DATABASE');
    
    // Create document collections
    db._create('nodes');
    db._create('documents');
    
    // Create edge collections
    db._createEdgeCollection('edges');
    db._createEdgeCollection('references');
    
    print('Created base collections in $ARANGO_DATABASE');
  } catch (e) {
    print('Error resetting ArangoDB: ' + e.message);
    throw e;
  }
EOF
  
  # Execute the JS file with arangosh
  echo -e "  ${YELLOW}•${NC} Executing ArangoDB reset script..."
  arangosh \
    --server.endpoint tcp://127.0.0.1:8529 \
    --server.username "$DB_USER" \
    --server.password "$HADES_ARANGO_PASSWORD" \
    --javascript.execute "$TMP_JS_FILE"
  
  # Clean up temp file
  rm "$TMP_JS_FILE"
  
  echo -e "  ${GREEN}✓${NC} ArangoDB database reset successfully."
  return 0
}

# Main execution
echo "Starting database reset at $(date)"
echo "--------------------------------------------------------"

# Confirm deletion
if confirm_deletion; then
  # Reset PostgreSQL
  reset_postgresql
  PG_STATUS=$?
  
  # Reset ArangoDB
  reset_arangodb
  ARANGO_STATUS=$?
  
  echo "--------------------------------------------------------"
  
  # Report results
  if [ $PG_STATUS -eq 0 ] && [ $ARANGO_STATUS -eq 0 ]; then
    echo -e "${GREEN}All databases reset successfully!${NC}"
    exit 0
  elif [ $PG_STATUS -eq 0 ]; then
    echo -e "${YELLOW}PostgreSQL reset successfully, but ArangoDB reset failed.${NC}"
    exit 1
  elif [ $ARANGO_STATUS -eq 0 ]; then
    echo -e "${YELLOW}ArangoDB reset successfully, but PostgreSQL reset failed.${NC}"
    exit 1
  else
    echo -e "${RED}Both database resets failed.${NC}"
    exit 1
  fi
else
  exit 0
fi
