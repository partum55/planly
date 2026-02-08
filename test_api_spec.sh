#!/bin/bash
# Test script for AGENT_1_TASKS API specification
# Tests all 8 required endpoints

set -e  # Exit on error

BASE_URL="http://localhost:8000"
EMAIL="test_$(date +%s)@example.com"  # Unique email for each test run
PASSWORD="testpass123"
ACCESS_TOKEN=""
REFRESH_TOKEN=""
CONVERSATION_ID=""

echo "========================================="
echo "Testing Planly API (AGENT_1_TASKS spec)"
echo "========================================="
echo ""
echo "Base URL: $BASE_URL"
echo "Test Email: $EMAIL"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_TOTAL=0

test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4
    local auth_header=$5

    ((TESTS_TOTAL++))
    echo -n "[$TESTS_TOTAL] Testing $name... "

    if [ -z "$auth_header" ]; then
        response=$(curl -s -X $method "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    else
        response=$(curl -s -X $method "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -H "$auth_header" \
            -d "$data")
    fi

    if echo "$response" | jq . >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((TESTS_PASSED++))
        echo "$response" | jq .
        echo ""
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        echo "Response: $response"
        echo ""
        return 1
    fi
}

# 1. Test POST /auth/register
echo "1. POST /auth/register"
echo "======================"
response=$(curl -s -X POST "$BASE_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"full_name\":\"Test User\"}")

if echo "$response" | jq -e '.access_token' >/dev/null 2>&1; then
    ACCESS_TOKEN=$(echo "$response" | jq -r '.access_token')
    REFRESH_TOKEN=$(echo "$response" | jq -r '.refresh_token')
    USER_ID=$(echo "$response" | jq -r '.user_id')
    echo -e "${GREEN}✓ PASS${NC} - User registered"
    echo "User ID: $USER_ID"
    echo "Access Token: ${ACCESS_TOKEN:0:20}..."
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "$response"
fi
((TESTS_TOTAL++))
echo ""

# 2. Test POST /auth/login
echo "2. POST /auth/login"
echo "==================="
response=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

if echo "$response" | jq -e '.access_token' >/dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC} - Login successful"
    echo "$response" | jq .
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "$response"
fi
((TESTS_TOTAL++))
echo ""

# 3. Test POST /auth/refresh
echo "3. POST /auth/refresh"
echo "====================="
response=$(curl -s -X POST "$BASE_URL/auth/refresh" \
    -H "Content-Type: application/json" \
    -d "{\"refresh_token\":\"$REFRESH_TOKEN\"}")

if echo "$response" | jq -e '.access_token' >/dev/null 2>&1; then
    NEW_ACCESS_TOKEN=$(echo "$response" | jq -r '.access_token')
    ACCESS_TOKEN=$NEW_ACCESS_TOKEN  # Update for subsequent tests
    echo -e "${GREEN}✓ PASS${NC} - Token refreshed"
    echo "New Access Token: ${ACCESS_TOKEN:0:20}..."
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "$response"
fi
((TESTS_TOTAL++))
echo ""

# 4. Test GET /auth/me
echo "4. GET /auth/me"
echo "==============="
response=$(curl -s -X GET "$BASE_URL/auth/me" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

if echo "$response" | jq -e '.user_id' >/dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC} - User profile retrieved"
    echo "$response" | jq .
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "$response"
fi
((TESTS_TOTAL++))
echo ""

# 5. Test POST /auth/link-telegram
echo "5. POST /auth/link-telegram"
echo "==========================="
response=$(curl -s -X POST "$BASE_URL/auth/link-telegram" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"telegram_id\":123456789,\"telegram_username\":\"testuser\"}")

if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC} - Telegram account linked"
    echo "$response" | jq .
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "$response"
fi
((TESTS_TOTAL++))
echo ""

# 6. Test POST /agent/process
echo "6. POST /agent/process"
echo "======================"
response=$(curl -s -X POST "$BASE_URL/agent/process" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -d '{
      "user_prompt": "Schedule dinner tomorrow at 7pm",
      "source": "desktop_screenshot",
      "context": {
        "messages": [
          {"username":"Alice","text":"Lets do dinner tomorrow","timestamp":"2026-02-09T19:00:00Z"},
          {"username":"Bob","text":"7pm works for me","timestamp":"2026-02-09T19:01:00Z"}
        ],
        "screenshot_metadata": {
          "ocr_confidence": 85.5,
          "raw_text": "Alice: Lets do dinner tomorrow\nBob: 7pm works for me"
        }
      }
    }')

if echo "$response" | jq -e '.conversation_id' >/dev/null 2>&1; then
    CONVERSATION_ID=$(echo "$response" | jq -r '.conversation_id')
    ACTION_ID=$(echo "$response" | jq -r '.blocks[] | select(.type=="action_cards") | .actions[0].action_id')
    echo -e "${GREEN}✓ PASS${NC} - Conversation processed"
    echo "Conversation ID: $CONVERSATION_ID"
    echo "Response blocks:"
    echo "$response" | jq '.blocks'
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "$response"
fi
((TESTS_TOTAL++))
echo ""

# 7. Test POST /agent/confirm-actions
echo "7. POST /agent/confirm-actions"
echo "==============================="
if [ -n "$ACTION_ID" ] && [ "$ACTION_ID" != "null" ]; then
    response=$(curl -s -X POST "$BASE_URL/agent/confirm-actions" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -d "{
          \"conversation_id\": \"$CONVERSATION_ID\",
          \"action_ids\": [\"$ACTION_ID\"]
        }")

    if echo "$response" | jq -e '.results' >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC} - Actions confirmed"
        echo "$response" | jq .
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}"
        echo "$response"
    fi
else
    echo -e "${RED}⊘ SKIP${NC} - No actions to confirm (agent didn't return action cards)"
fi
((TESTS_TOTAL++))
echo ""

# 8. Test POST /auth/google/callback (skip - requires real OAuth code)
echo "8. POST /auth/google/callback"
echo "=============================="
echo -e "${GREEN}⊘ SKIP${NC} - Requires real Google OAuth authorization code"
echo "To test: Set up Google OAuth in console.cloud.google.com"
echo "         and perform actual OAuth flow from desktop app"
((TESTS_TOTAL++))
echo ""

# Summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo "Tests passed: $TESTS_PASSED / $TESTS_TOTAL"
echo ""

if [ $TESTS_PASSED -eq $((TESTS_TOTAL - 1)) ]; then
    echo -e "${GREEN}✓ All testable endpoints PASSED!${NC}"
    echo "Backend is ready for Agent 2 integration."
    exit 0
else
    echo -e "${RED}✗ Some tests FAILED${NC}"
    exit 1
fi
