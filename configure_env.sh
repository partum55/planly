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
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 1: Supabase Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📚 See GET_SUPABASE_CREDENTIALS.md for detailed help"
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

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 2: LLM Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Choose your LLM provider:"
echo "  1) Cloud API (Recommended) - Groq, Together AI, or OpenRouter"
echo "  2) Local Ollama - Requires local installation"
echo ""
read -p "Enter choice (1 or 2): " llm_choice

if [ "$llm_choice" = "1" ]; then
    echo ""
    echo "Cloud LLM Providers:"
    echo "  1) Groq (Fastest, Free tier)"
    echo "  2) Together AI (Good balance, \$25 free credits)"
    echo "  3) OpenRouter (Most model options)"
    echo ""
    read -p "Choose provider (1, 2, or 3): " provider_choice

    case $provider_choice in
        1)
            llm_provider="Groq"
            llm_endpoint="https://api.groq.com/openai"
            llm_model="llama-3.1-8b-instant"
            echo ""
            echo "📚 Get your Groq API key at: https://console.groq.com/"
            ;;
        2)
            llm_provider="Together AI"
            llm_endpoint="https://api.together.xyz"
            llm_model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
            echo ""
            echo "📚 Get your Together AI API key at: https://api.together.xyz/"
            ;;
        3)
            llm_provider="OpenRouter"
            llm_endpoint="https://openrouter.ai/api"
            llm_model="meta-llama/llama-3.1-8b-instruct"
            echo ""
            echo "📚 Get your OpenRouter API key at: https://openrouter.ai/"
            ;;
        *)
            echo "Invalid choice. Defaulting to Groq."
            llm_provider="Groq"
            llm_endpoint="https://api.groq.com/openai"
            llm_model="llama-3.1-8b-instant"
            ;;
    esac

    echo ""
    read -p "🔑 Enter your $llm_provider API Key: " llm_api_key

    if [ -z "$llm_api_key" ]; then
        echo "⚠️  Warning: No API key provided. You'll need to add it later."
        llm_api_key="YOUR_API_KEY_HERE"
    fi

    use_cloud_llm="true"
    ollama_endpoint="$llm_endpoint"
    ollama_model="$llm_model"

elif [ "$llm_choice" = "2" ]; then
    echo ""
    echo "Local Ollama selected."
    echo "📚 Install: curl -fsSL https://ollama.com/install.sh | sh"
    echo "📚 Pull model: ollama pull llama3.1:8b"

    use_cloud_llm="false"
    ollama_endpoint="http://localhost:11434"
    ollama_model="llama3.1:8b"
    llm_api_key=""
else
    echo "Invalid choice. Defaulting to Cloud (Groq)."
    use_cloud_llm="true"
    ollama_endpoint="https://api.groq.com/openai"
    ollama_model="llama-3.1-8b-instant"
    llm_api_key="YOUR_GROQ_API_KEY_HERE"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Step 3: Optional Features"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Google OAuth (for desktop app)
echo "Google OAuth (for desktop app 'Continue with Google' button):"
read -p "  Google Client ID (optional, press Enter to skip): " google_client_id
if [ -n "$google_client_id" ]; then
    read -p "  Google Client Secret: " google_client_secret
else
    google_client_secret=""
fi

# Google Calendar
echo ""
echo "Google Calendar (for event creation):"
read -p "  Calendar ID (optional, press Enter to skip): " calendar_id

# Generate JWT secret
jwt_secret=$(openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))")

echo ""
echo "Generating secure JWT secret..."

# Create .env file
echo ""
echo "Creating .env file..."

cat > .env << EOF
# Database Configuration
SUPABASE_URL=$supabase_url
SUPABASE_KEY=$supabase_key

# LLM Configuration
USE_CLOUD_LLM=$use_cloud_llm
OLLAMA_ENDPOINT=$ollama_endpoint
OLLAMA_MODEL=$ollama_model
LLM_API_KEY=$llm_api_key

# Alternative Cloud Providers (change OLLAMA_ENDPOINT and OLLAMA_MODEL):
# Groq: https://api.groq.com/openai, model: llama-3.1-8b-instant
# Together AI: https://api.together.xyz, model: meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
# OpenRouter: https://openrouter.ai/api, model: meta-llama/llama-3.1-8b-instruct

# Google Calendar (Optional)
GOOGLE_CALENDAR_ID=${calendar_id:-}
GOOGLE_SERVICE_ACCOUNT_FILE=./integrations/google_calendar/service_account.json

# Google OAuth (for desktop app "Continue with Google")
GOOGLE_CLIENT_ID=${google_client_id:-}
GOOGLE_CLIENT_SECRET=${google_client_secret:-}

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
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Configuration Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Created: server/.env"
echo ""

if [ "$use_cloud_llm" = "true" ]; then
    if [ "$llm_api_key" = "YOUR_API_KEY_HERE" ] || [ "$llm_api_key" = "YOUR_GROQ_API_KEY_HERE" ]; then
        echo "⚠️  IMPORTANT: Add your LLM API key to server/.env"
        echo "   Current placeholder: $llm_api_key"
        echo ""
    fi
    echo "🤖 LLM: $llm_provider (Cloud API)"
    echo "   Endpoint: $ollama_endpoint"
    echo "   Model: $ollama_model"
else
    echo "🤖 LLM: Local Ollama"
    echo "   Make sure to:"
    echo "   1. Install: curl -fsSL https://ollama.com/install.sh | sh"
    echo "   2. Pull model: ollama pull llama3.1:8b"
    echo "   3. Start: ollama serve"
fi

echo ""
echo "🔒 Security reminders:"
echo "   • Never commit .env to git (it's already in .gitignore)"
echo "   • Never share your service_role key or API keys"
echo "   • Generated secure JWT secret automatically"
echo ""
echo "📋 Next steps:"
echo "   1. Run database schema: See SUPABASE_SETUP_CHECKLIST.md"
echo "   2. Start the server: ./run_server.sh"
echo "   3. Test the API: ./server/test_api.sh"
echo ""
echo "📚 Documentation:"
echo "   • API docs: QUICK_START.md"
echo "   • LLM setup: CLOUD_LLM_SETUP.md"
echo "   • Database: SUPABASE_SETUP_CHECKLIST.md"
echo ""
