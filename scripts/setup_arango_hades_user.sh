#!/bin/bash
# Script to create and configure the 'hades' user in ArangoDB
# To be run after resetting the root password

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
USER="hades"
DB_NAME="hades_graph"

echo -e "${YELLOW}This script will create the '${USER}' user in ArangoDB with appropriate permissions.${NC}"
echo -e "${YELLOW}Please enter the ArangoDB root password:${NC}"
read -s ROOT_PASSWORD
echo

echo -e "${YELLOW}Enter a password for the 'hades' user:${NC}"
read -s HADES_PASSWORD
echo

echo -e "${YELLOW}Setting up ArangoDB user and database...${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$(dirname "$0")"
JS_SCRIPT="$SCRIPT_DIR/setup_arango_db.js"

# Check if the JavaScript file exists
if [ ! -f "$JS_SCRIPT" ]; then
  echo -e "${RED}Error: JavaScript file not found: $JS_SCRIPT${NC}"
  exit 1
fi

# Use arangosh to create the hades user and assign permissions
arangosh \
  --server.endpoint tcp://127.0.0.1:8529 \
  --server.username root \
  --server.password "$ROOT_PASSWORD" \
  --javascript.execute "$JS_SCRIPT" \
  -- "$USER" "$HADES_PASSWORD" "$DB_NAME"

# Verify access with the new user
echo -e "${YELLOW}Verifying $USER user access to $DB_NAME...${NC}"
arangosh \
  --server.endpoint tcp://127.0.0.1:8529 \
  --server.username "$USER" \
  --server.password "$HADES_PASSWORD" \
  --server.database "$DB_NAME" \
  --javascript.execute-string "print('Successfully connected as $USER to database $DB_NAME'); print('Available collections:'); db._collections().forEach(function(col) { print(' - ' + col.name()); });"

echo -e "${GREEN}ArangoDB user and database setup complete!${NC}"
echo -e "${GREEN}The 'hades' user now has full access to the '$DB_NAME' database.${NC}"
echo -e "${YELLOW}Make sure to update your .env file with the new credentials:${NC}"
echo "HADES_ARANGO_USER=$USER"
echo "HADES_ARANGO_PASSWORD=[your_password]"
echo "HADES_ARANGO_DATABASE=$DB_NAME"
