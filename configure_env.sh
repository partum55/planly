#!/bin/bash
# Interactive script to configure .env file

echo "╔════════════════════════════════════════╗"
echo "║   Planly Environment Configuration     ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Navigate to server directory
cd "$(dirname "$0")/server" || exit 1

# Check if .env exists
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists."
    read -p "Do you want to overwrite it? (y/N): " overwrite
    if [[ ! $overwrite =~ ^[Yy]$ ]]; then
        echo "Keeping existing .env file."
        echo "Edit it manually if needed: nano server/.env"
        exit 0
    fi
fi

echo ""
echo "Please provide your Supabase credentials:"
echo "(See GET_SUPABASE_CREDENTIALS.md for help)"
echo ""

# Get Supabase URL
read -p "📍 Supabase Project URL (https://xxxxx.supabase.co): " supabase_url
if [ -z "$supabase_url" ]; then
    echo "❌ Supabase URL is required!"
    exit 1
fi

# Get Supabase Key
read -p "🔑 Supabase Service Role Key (starts with eyJ...): " supabase_key
if [ -z "$supabase_key" ]; then
    echo "❌ Supabase key is required!"
    exit 1
fi

# Generate JWT secret
jwt_secret=$(openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))")

echo ""
echo "Generating secure JWT secret..."
echo ""

# Optional: Google Calendar
read -p "📅 Google Calendar ID (optional, press Enter to skip): " calendar_id

echo ""
echo "Creating .env file..."

# Create .env file
cat > .env << EOF
# Supabase Configuration
SUPABASE_URL=$supabase_url
SUPABASE_KEY=$supabase_key

# Ollama LLM
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Google Calendar (Optional)
GOOGLE_CALENDAR_ID=${calendar_id:-}
GOOGLE_SERVICE_ACCOUNT_FILE=./integrations/google_calendar/service_account.json

# External APIs (Optional)
YELP_API_KEY=
GOOGLE_PLACES_API_KEY=

# Authentication
JWT_SECRET_KEY=$jwt_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Context Management
CONTEXT_WINDOW_MINUTES=60
EOF

echo ""
echo "✅ Configuration complete!"
echo ""
echo "📝 Created: server/.env"
echo ""
echo "🔒 Security reminders:"
echo "   • Never commit .env to git (it's already in .gitignore)"
echo "   • Never share your service_role key"
echo "   • Generated secure JWT secret automatically"
echo ""
echo "Next steps:"
echo "   1. Make sure Ollama is installed and running"
echo "   2. Run: ollama pull llama3.1:8b"
echo "   3. Start the server: ./run_server.sh"
echo ""
