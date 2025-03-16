#!/bin/bash
# Script to reset the ArangoDB root password
# Run with sudo

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root (use sudo)${NC}"
  exit 1
fi

echo -e "${YELLOW}This script will reset the ArangoDB root password.${NC}"
echo -e "${YELLOW}Enter a new root password for ArangoDB:${NC}"
read -s NEW_ROOT_PASSWORD
echo

if [ -z "$NEW_ROOT_PASSWORD" ]; then
  echo -e "${RED}Password cannot be empty.${NC}"
  exit 1
fi

echo -e "${YELLOW}Stopping ArangoDB service...${NC}"
systemctl stop arangodb3

# Create a temporary password update JavaScript file
TMP_JS_FILE=$(mktemp)
cat > "$TMP_JS_FILE" <<EOF
require('@arangodb/users').update('root', '$NEW_ROOT_PASSWORD');
print('Root password updated successfully');
quit();
EOF

echo -e "${YELLOW}Starting ArangoDB temporarily with authentication disabled...${NC}"

# Start ArangoDB without authentication in the background
TMP_PID_FILE=$(mktemp)
sudo -u arangodb arangod --server.authentication false --pid-file="$TMP_PID_FILE" --log.foreground-tty false &
BG_PID=$!

# Wait for ArangoDB to start up
echo -e "${YELLOW}Waiting for ArangoDB to start...${NC}"
sleep 10

# Wait to make sure ArangoDB is fully started
sleep 5

# Check if PID file exists and contains a valid PID
if [ -f "$TMP_PID_FILE" ] && [ -s "$TMP_PID_FILE" ]; then
  ARANGO_PID=$(cat "$TMP_PID_FILE")
  echo -e "${GREEN}ArangoDB started with PID: $ARANGO_PID${NC}"
else
  # If PID file doesn't exist or is empty, use the background process ID
  echo -e "${YELLOW}PID file empty or not found, using background PID: $BG_PID${NC}"
  ARANGO_PID=$BG_PID
fi

# Execute the password update
echo -e "${YELLOW}Updating root password...${NC}"
arangosh --javascript.execute "$TMP_JS_FILE"
PASSWORD_UPDATE_RESULT=$?

# Clean up temp file
rm "$TMP_JS_FILE"

# Stop the temporary ArangoDB instance
echo -e "${YELLOW}Stopping temporary ArangoDB instance...${NC}"
if [ -n "$ARANGO_PID" ] && [ "$ARANGO_PID" -gt 0 ] 2>/dev/null; then
  kill -TERM $ARANGO_PID 2>/dev/null || true
else
  echo -e "${YELLOW}No valid PID found, attempting to stop ArangoDB using other methods...${NC}"
  # Try to kill by process name as fallback
  pkill -f "arangod --server.authentication false" 2>/dev/null || true
fi
sleep 5

# Start ArangoDB service normally
echo -e "${YELLOW}Starting ArangoDB service with authentication enabled...${NC}"
systemctl start arangodb3

# Check if the password update was successful
if [ $PASSWORD_UPDATE_RESULT -eq 0 ]; then
  echo -e "${GREEN}ArangoDB root password has been successfully reset!${NC}"
  echo -e "${GREEN}You can now connect using the new password.${NC}"
else
  echo -e "${RED}Failed to update ArangoDB root password.${NC}"
  exit 1
fi
