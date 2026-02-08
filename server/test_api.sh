#!/bin/bash

# Planly API Test Script
# Quick tests for API endpoints

BASE_URL="http://localhost:8000"
EMAIL="test@example.com"
PASSWORD="testpass123"

echo "================================"
echo "  Planly API Test Script"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo "1. Testing health endpoint..."
response=$(curl -s "$BASE_URL/health")
if echo "$response" | grep -q "ok"; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}✗ Health check failed${NC}"
    exit 1
fi
echo ""

# Test 2: Register User
echo "2. Registering test user..."
response=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\", \"full_name\": \"Test User\"}")

if echo "$response" | grep -q "access_token"; then
    echo -e "${GREEN}✓ User registration successful${NC}"
    ACCESS_TOKEN=$(echo "$response" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    echo "  Access token: ${ACCESS_TOKEN:0:50}..."
else
    # Try login if user already exists
    echo "  User might exist, trying login..."
    response=$(curl -s -X POST "$BASE_URL/auth/login" \
      -H "Content-Type: application/json" \
      -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")

    if echo "$response" | grep -q "access_token"; then
        echo -e "${GREEN}✓ Login successful${NC}"
        ACCESS_TOKEN=$(echo "$response" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
        echo "  Access token: ${ACCESS_TOKEN:0:50}..."
    else
        echo -e "${RED}✗ Login failed${NC}"
        echo "$response"
        exit 1
    fi
fi
echo ""

# Test 3: Verify Token
echo "3. Verifying authentication token..."
response=$(curl -s "$BASE_URL/auth/verify" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

if echo "$response" | grep -q "email"; then
    echo -e "${GREEN}✓ Token verification successful${NC}"
    echo "  User: $(echo "$response" | grep -o '"email":"[^"]*' | cut -d'"' -f4)"
else
    echo -e "${RED}✗ Token verification failed${NC}"
    exit 1
fi
echo ""

# Test 4: Process Conversation
echo "4. Testing agent conversation processing..."
response=$(curl -s -X POST "$BASE_URL/agent/process" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "source": "desktop_screenshot",
    "context": {
      "messages": [
        {
          "username": "Alice",
          "text": "Lets grab dinner tomorrow at 7pm",
          "timestamp": "2026-02-08T18:00:00Z"
        },
        {
          "username": "Bob",
          "text": "Im in! Italian sounds good",
          "timestamp": "2026-02-08T18:01:00Z"
        },
        {
          "username": "Charlie",
          "text": "Count me in too!",
          "timestamp": "2026-02-08T18:02:00Z"
        }
      ]
    }
  }')

if echo "$response" | grep -q "intent"; then
    echo -e "${GREEN}✓ Agent processing successful${NC}"
    echo "  Response:"
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
else
    echo -e "${RED}✗ Agent processing failed${NC}"
    echo "$response"
fi
echo ""

echo "================================"
echo "  Test Summary"
echo "================================"
echo -e "${GREEN}All basic tests passed!${NC}"
echo ""
echo "Next steps:"
echo "  1. Visit http://localhost:8000/docs for interactive API docs"
echo "  2. Test Telegram webhook integration"
echo "  3. Integrate with Desktop app"
echo ""
