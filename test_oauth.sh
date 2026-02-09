#!/bin/bash
# Test Google OAuth integration

set -e

BASE_URL="${1:-http://localhost:8000}"

echo "╔════════════════════════════════════════╗"
echo "║   Google OAuth Integration Test        ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "Base URL: $BASE_URL"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check if OAuth endpoint exists
echo "Test 1: Checking OAuth endpoints..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if curl -s "$BASE_URL/docs" | grep -q "google/auth-url"; then
    echo -e "${GREEN}✓ GET /auth/google/auth-url exists${NC}"
else
    echo -e "${YELLOW}⚠ GET /auth/google/auth-url not found in docs${NC}"
fi

if curl -s "$BASE_URL/docs" | grep -q "google/callback"; then
    echo -e "${GREEN}✓ POST /auth/google/callback exists${NC}"
else
    echo -e "${RED}✗ POST /auth/google/callback not found in docs${NC}"
fi
echo ""

# Test 2: Get auth URL
echo "Test 2: Getting Google OAuth URL..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

response=$(curl -s "$BASE_URL/auth/google/auth-url" 2>&1)

if echo "$response" | jq . >/dev/null 2>&1; then
    if echo "$response" | jq -e '.auth_url' >/dev/null 2>&1; then
        auth_url=$(echo "$response" | jq -r '.auth_url')
        client_id=$(echo "$response" | jq -r '.client_id')

        if [[ "$client_id" == "null" ]] || [[ -z "$client_id" ]]; then
            echo -e "${YELLOW}⚠ OAuth not configured${NC}"
            echo "  Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in server/.env"
            echo ""
            echo "  See GOOGLE_OAUTH_SETUP.md for setup instructions"
        else
            echo -e "${GREEN}✓ OAuth is configured${NC}"
            echo "  Client ID: ${client_id:0:30}..."
            echo "  Auth URL: ${auth_url:0:80}..."
        fi
    else
        echo -e "${RED}✗ Failed to get auth URL${NC}"
        echo "$response" | jq .
    fi
else
    echo -e "${RED}✗ Invalid response${NC}"
    echo "$response"
fi
echo ""

# Test 3: Check OAuth callback endpoint
echo "Test 3: Checking OAuth callback endpoint..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

response=$(curl -s -X POST "$BASE_URL/auth/google/callback" \
    -H "Content-Type: application/json" \
    -d '{"code":"test_invalid_code"}' 2>&1)

if echo "$response" | grep -q "OAuth authentication failed\|Invalid authorization code\|not configured"; then
    echo -e "${GREEN}✓ Callback endpoint is working${NC}"
    echo "  (Expected error for invalid code)"
else
    echo -e "${YELLOW}⚠ Unexpected response${NC}"
    echo "$response" | head -3
fi
echo ""

# Summary
echo "╔════════════════════════════════════════╗"
echo "║   Test Summary                         ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Check if OAuth is configured
if [[ "$client_id" != "null" ]] && [[ -n "$client_id" ]]; then
    echo -e "${GREEN}✅ Google OAuth is configured and ready!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Desktop app can get auth URL from: GET $BASE_URL/auth/google/auth-url"
    echo "  2. Open auth_url in browser for user to login"
    echo "  3. Capture authorization code from redirect"
    echo "  4. POST code to: $BASE_URL/auth/google/callback"
    echo "  5. Receive JWT tokens for authenticated user"
else
    echo -e "${YELLOW}⚠ Google OAuth is NOT configured${NC}"
    echo ""
    echo "To enable Google OAuth:"
    echo "  1. Follow GOOGLE_OAUTH_SETUP.md guide (15 minutes)"
    echo "  2. Get Client ID and Secret from Google Cloud Console"
    echo "  3. Add to server/.env:"
    echo "     GOOGLE_CLIENT_ID=your_client_id"
    echo "     GOOGLE_CLIENT_SECRET=your_client_secret"
    echo "  4. Restart server"
    echo ""
    echo "Documentation:"
    echo "  📚 Setup guide: GOOGLE_OAUTH_SETUP.md"
    echo "  📚 API docs: $BASE_URL/docs"
fi
echo ""
