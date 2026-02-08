# 🌥️ Cloud LLM Setup Guide

The Planly backend now supports **cloud-based LLM APIs** instead of requiring local Ollama installation!

## ✅ Why Use Cloud APIs?

- **No Local Setup:** No need to install Ollama or download large models
- **Faster Inference:** Cloud providers have optimized infrastructure
- **Better Reliability:** Professional hosting with high uptime
- **Easy Scaling:** No hardware limitations

---

## 🎯 Recommended Providers

### 1. **Together AI** (Recommended for Hackathon)
**Best for:** Good balance of speed, cost, and reliability

#### Setup:
1. Go to https://api.together.xyz/
2. Sign up for free account
3. Get $25 free credits (no credit card required)
4. Go to **Settings → API Keys**
5. Create new API key
6. Copy the key

#### Configuration:
```bash
USE_CLOUD_LLM=true
OLLAMA_ENDPOINT=https://api.together.xyz
OLLAMA_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
LLM_API_KEY=your_together_ai_key_here
```

**Pricing:** ~$0.20 per 1M tokens (very cheap for hackathon)

---

### 2. **Groq** (Fastest Option)
**Best for:** Maximum speed - 10x faster than others!

#### Setup:
1. Go to https://console.groq.com/
2. Sign up with Google/GitHub
3. Get free API key (generous free tier)
4. Copy API key from dashboard

#### Configuration:
```bash
USE_CLOUD_LLM=true
OLLAMA_ENDPOINT=https://api.groq.com/openai
OLLAMA_MODEL=llama-3.1-8b-instant
LLM_API_KEY=your_groq_key_here
```

**Pricing:** Free tier includes 14,400 requests/day

---

### 3. **OpenRouter** (Most Options)
**Best for:** Access to many different models

#### Setup:
1. Go to https://openrouter.ai/
2. Sign up and add credits ($5 minimum)
3. Get API key from **Keys** section

#### Configuration:
```bash
USE_CLOUD_LLM=true
OLLAMA_ENDPOINT=https://openrouter.ai/api
OLLAMA_MODEL=meta-llama/llama-3.1-8b-instruct
LLM_API_KEY=your_openrouter_key_here
```

---

## 🚀 Quick Start

### Step 1: Choose a Provider
Pick one from above (we recommend **Groq** for free and fast, or **Together AI** for best hackathon experience)

### Step 2: Get API Key
Follow the setup instructions for your chosen provider

### Step 3: Update `.env` File
Edit `/windows/E/Programming/Hackathon/SoftServe/planly/server/.env`:

```bash
# LLM Configuration - Cloud API
USE_CLOUD_LLM=true
OLLAMA_ENDPOINT=https://api.together.xyz  # or groq, openrouter
OLLAMA_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
LLM_API_KEY=YOUR_ACTUAL_API_KEY_HERE
```

### Step 4: Restart Server
```bash
venv/bin/python server/main.py
```

### Step 5: Test It
Visit http://localhost:8000/docs and try the `/agent/process` endpoint!

---

## 🔧 Troubleshooting

### "Invalid API key" error
- Double-check you copied the full API key
- Make sure no extra spaces in `.env` file
- Verify the key is active in provider dashboard

### "Model not found" error
- Check the model name matches the provider
- Together AI: `meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo`
- Groq: `llama-3.1-8b-instant`
- OpenRouter: `meta-llama/llama-3.1-8b-instruct`

### Rate limit errors
- Groq free tier: 14,400 requests/day
- Together AI: $25 free credits
- Add billing if you hit limits

---

## 💡 Cost Estimates (for Hackathon)

Assuming 1000 requests during hackathon weekend:

| Provider | Cost | Free Tier |
|----------|------|-----------|
| **Groq** | $0 | 14,400 requests/day |
| **Together AI** | ~$2-5 | $25 free credits |
| **OpenRouter** | ~$3-7 | Pay as you go |

**Recommendation:** Start with Groq (free), switch to Together AI if you hit limits.

---

## 🎓 Advanced: Multiple Providers

You can configure different models for different purposes by creating separate client instances:

```python
# In your code
from integrations.ollama.client import OllamaClient

# Fast model for quick responses
fast_client = OllamaClient(
    endpoint="https://api.groq.com/openai",
    model="llama-3.1-8b-instant"
)

# Powerful model for complex reasoning
smart_client = OllamaClient(
    endpoint="https://api.together.xyz",
    model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
)
```

---

## 📚 API Documentation

- **Together AI:** https://docs.together.ai/
- **Groq:** https://console.groq.com/docs
- **OpenRouter:** https://openrouter.ai/docs

---

## ⚡ Performance Comparison

| Provider | Speed | Cost | Models | Free Tier |
|----------|-------|------|--------|-----------|
| **Groq** | ⚡⚡⚡⚡⚡ | Free | Limited | Generous |
| **Together AI** | ⚡⚡⚡⚡ | Low | Many | $25 credits |
| **OpenRouter** | ⚡⚡⚡ | Medium | Most | Pay as you go |

---

## 🔄 Switching Back to Local Ollama

If you want to use local Ollama instead:

1. Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
2. Pull model: `ollama pull llama3.1:8b`
3. Update `.env`:
   ```bash
   USE_CLOUD_LLM=false
   OLLAMA_ENDPOINT=http://localhost:11434
   OLLAMA_MODEL=llama3.1:8b
   LLM_API_KEY=  # Leave empty
   ```

---

## 🎉 Ready to Go!

With cloud LLM configured:
1. ✅ No local setup needed
2. ✅ Faster inference
3. ✅ Professional-grade reliability
4. ✅ Focus on building features, not infrastructure

Happy hacking! 🚀
