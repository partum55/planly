# Planly Deployment Guide: DigitalOcean App Platform

**Simplified deployment using DigitalOcean's managed platform**

**Total Time Estimate:** 15-20 minutes (fully automated after setup)

**Last Updated:** 2026-02-09

---

## 📋 What is App Platform?

**App Platform** is DigitalOcean's Platform-as-a-Service (PaaS) that automatically handles:
- ✅ Server provisioning and management
- ✅ Container orchestration
- ✅ Auto-scaling based on traffic
- ✅ SSL/HTTPS certificates (automatic)
- ✅ Load balancing
- ✅ Health checks and monitoring
- ✅ CI/CD from GitHub/GitLab
- ✅ Zero-downtime deployments

**vs Traditional Droplet:**
| Feature | Droplet | App Platform |
|---------|---------|--------------|
| Setup Time | 40 minutes | 15 minutes |
| Server Management | Manual | Automatic |
| SSL Setup | Manual | Automatic |
| Scaling | Manual | Automatic |
| Cost | $6-12/month | $12-24/month |
| Best For | Full control | Simplicity |

---

## 💰 Cost Comparison

**App Platform Pricing:**

| Tier | vCPU | RAM | Price | Best For |
|------|------|-----|-------|----------|
| **Basic** | 1 vCPU | 512MB | $5/month | Dev/Testing |
| **Professional** | 1 vCPU | 1GB | $12/month | **Recommended for Hackathon** |
| **Professional** | 2 vCPU | 2GB | $24/month | Production |

**Total Monthly Cost:**
- App Platform: $12/month (recommended)
- Supabase: Free tier
- Groq LLM: Free tier
- SSL: Included free
- **Total: $12/month**

---

## 📋 Prerequisites

**Time: 5-10 minutes**

Before starting, have ready:
- [ ] DigitalOcean account ([Sign up](https://www.digitalocean.com/))
- [ ] GitHub or GitLab account
- [ ] Code pushed to GitHub repository
- [ ] Supabase project credentials
- [ ] Cloud LLM API key (Groq, Together AI, or OpenRouter)

### 1. Push Code to GitHub (if not already done)

```bash
# In your local planly directory
git remote add origin https://github.com/yourusername/planly.git
git push -u origin main
```

**Time:** 2 minutes

### 2. Prepare for Deployment

Make sure your repository has:
- ✅ `server/requirements.txt` - Python dependencies
- ✅ `server/main.py` - Application entry point
- ✅ `server/.env.template` - Environment variable template

---

## 🚀 Deployment Steps

### Step 1: Create App (3 minutes)

**Time:** ~3 minutes

1. **Go to App Platform:**
   - Log into DigitalOcean: https://cloud.digitalocean.com/
   - Click "Apps" in left sidebar
   - Click "Create App"

2. **Connect Repository:**
   - **Source:** GitHub or GitLab
   - Click "Manage Access" if first time
   - Authorize DigitalOcean
   - Select repository: `yourusername/planly`
   - **Branch:** `main`
   - **Autodeploy:** ✓ (checked) - Auto-deploy on git push
   - Click "Next"

   **Time:** 2 minutes (including authorization)

3. **Configure Resources:**
   - App Platform auto-detects Python app
   - If not detected, click "Edit" and configure:

   **Source Directory:** `/server`

   **Build Command:**
   ```bash
   pip install -r requirements.txt
   ```

   **Run Command:**
   ```bash
   python main.py
   ```

   **HTTP Port:** `8000` (App Platform will automatically map to 443)

   **Time:** 1 minute

4. **Name Your App:**
   - **App Name:** `planly-backend`
   - This becomes your URL: `planly-backend-xxxxx.ondigitalocean.app`
   - Click "Next"

---

### Step 2: Configure Environment Variables (5 minutes)

**Time:** ~5 minutes

1. **In App Platform Settings:**
   - Before clicking "Create Resources", scroll to "Environment Variables"
   - Click "Edit" next to the component

2. **Add All Environment Variables:**

   Click "Add Variable" for each:

   | Key | Value | Type |
   |-----|-------|------|
   | `SUPABASE_URL` | `https://xxx.supabase.co` | Text |
   | `SUPABASE_KEY` | `eyJ...` (service_role key) | Secret |
   | `USE_CLOUD_LLM` | `true` | Text |
   | `OLLAMA_ENDPOINT` | `https://api.groq.com/openai` | Text |
   | `OLLAMA_MODEL` | `llama-3.1-8b-instant` | Text |
   | `LLM_API_KEY` | Your Groq/Together AI key | Secret |
   | `JWT_SECRET_KEY` | Generate: `openssl rand -base64 32` | Secret |
   | `JWT_ALGORITHM` | `HS256` | Text |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Text |
   | `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Text |
   | `HOST` | `0.0.0.0` | Text |
   | `PORT` | `8000` | Text |
   | `LOG_LEVEL` | `INFO` | Text |
   | `CONTEXT_WINDOW_MINUTES` | `60` | Text |

   **Optional (Google OAuth):**
   | Key | Value | Type |
   |-----|-------|------|
   | `GOOGLE_CLIENT_ID` | Your client ID | Text |
   | `GOOGLE_CLIENT_SECRET` | Your secret | Secret |

   **Optional (Google Calendar):**
   | Key | Value | Type |
   |-----|-------|------|
   | `GOOGLE_CALENDAR_ID` | Your calendar ID | Text |

   **Note:** Mark sensitive values as "Secret" (encrypted)

   **Time:** 4 minutes

3. **Generate JWT Secret:**
   ```bash
   # Run locally to generate
   openssl rand -base64 32

   # Copy and paste as JWT_SECRET_KEY
   ```

4. **Click "Save" and then "Next"**

---

### Step 3: Select Plan (1 minute)

**Time:** ~1 minute

1. **Choose Plan:**
   - **Recommended:** Professional - $12/month
     - 1 vCPU, 1GB RAM
     - Perfect for hackathon/demo
     - Auto-scaling available

   - **Budget:** Basic - $5/month
     - 512MB RAM
     - Good for testing only

   - **Production:** Professional - $24/month
     - 2 vCPU, 2GB RAM
     - Better performance

2. **Select Region:**
   - Choose closest to your users
   - Examples: New York, San Francisco, London

3. **Click "Launch App"**

---

### Step 4: Wait for Deployment (5 minutes)

**Time:** ~5 minutes (automatic)

1. **Initial Build:**
   - App Platform pulls code from GitHub
   - Installs dependencies
   - Builds container
   - Deploys to infrastructure
   - Provisions SSL certificate
   - Sets up health checks

   **Watch Progress:**
   - You'll see build logs in real-time
   - Green checkmarks as steps complete

2. **Build Log Example:**
   ```
   ✓ Cloning repository
   ✓ Installing dependencies (pip install)
   ✓ Building container
   ✓ Deploying
   ✓ Health check passed
   ✓ SSL certificate issued
   ```

3. **Deployment Complete:**
   - Status changes to "Deployed"
   - You'll see a green "Live" badge
   - URL is active: `https://planly-backend-xxxxx.ondigitalocean.app`

---

### Step 5: Configure Database (3 minutes)

**Time:** ~3 minutes (in Supabase dashboard)

1. **Run Database Schema:**
   - Go to Supabase: https://app.supabase.com/
   - Select your project
   - SQL Editor → New Query
   - Copy contents of `server/database/supabase_schema.sql`
   - Click "Run"

   **Time:** 2 minutes

2. **Verify Tables:**
   - Table Editor
   - Should see 7 tables created

3. **Update App Settings (Optional):**
   - If needed, add database connection string to env vars
   - App Platform → Settings → Environment Variables
   - Changes trigger automatic redeployment

---

### Step 6: Add Custom Domain (Optional, 5 minutes)

**Time:** ~5 minutes + DNS propagation

**Skip this step if using default `.ondigitalocean.app` domain**

1. **In App Platform:**
   - Go to Settings → Domains
   - Click "Add Domain"

2. **Enter Domain:**
   - Domain: `api.yourdomain.com`
   - Click "Add Domain"

3. **Update DNS:**
   - App Platform shows required DNS records
   - Add CNAME record in your domain registrar:
     ```
     Type: CNAME
     Name: api
     Value: planly-backend-xxxxx.ondigitalocean.app
     TTL: 3600
     ```

4. **Wait for Verification:**
   - DNS propagation: 5-60 minutes
   - SSL certificate issued automatically
   - Status shows "Active" when ready

---

## 🧪 Testing Deployment (3 minutes)

**Time:** ~3 minutes

### 1. Get Your App URL

```bash
# Your app URL (from App Platform dashboard)
APP_URL="https://planly-backend-xxxxx.ondigitalocean.app"
```

### 2. Test Health Endpoint

```bash
curl $APP_URL/health
# Expected: {"status":"ok"}

curl $APP_URL/health/db
# Expected: Database connection info
```

### 3. Test API Documentation

```bash
# Open in browser
open $APP_URL/docs
```

### 4. Test Registration

```bash
curl -X POST $APP_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "full_name": "Test User"
  }'
```

**Expected:** JSON with access_token

### 5. Test Login

```bash
curl -X POST $APP_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

### 6. Test Agent Processing

```bash
TOKEN="your_access_token_here"

curl -X POST $APP_URL/agent/process \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "user_prompt": "Schedule dinner tomorrow",
    "source": "desktop_screenshot",
    "context": {
      "messages": [
        {"username":"Alice","text":"Dinner?","timestamp":"2026-02-09T19:00:00Z"}
      ]
    }
  }'
```

**Expected:** JSON with blocks array

---

## 📊 Monitoring & Management

### View Logs (Real-time)

1. **In App Platform:**
   - Go to your app
   - Click "Runtime Logs"
   - See live application logs

2. **Filter Logs:**
   - By time range
   - By component
   - By log level (info, error, etc.)

3. **Download Logs:**
   - Export logs for analysis
   - Up to 7 days history

### Performance Metrics

**In App Platform Dashboard:**
- **CPU Usage** - Real-time CPU utilization
- **Memory Usage** - RAM consumption
- **Request Count** - API requests per second
- **Response Time** - Average latency
- **Error Rate** - 4xx and 5xx responses

**Set Alerts:**
- Go to Settings → Alerts
- Configure email alerts for:
  - High CPU usage
  - Memory limits
  - Error rate spikes
  - Deployment failures

---

## 🔄 Continuous Deployment

### Automatic Deployments

**Already enabled!** Every git push triggers deployment:

```bash
# Make changes locally
git add .
git commit -m "Update feature"
git push origin main

# App Platform automatically:
# 1. Detects push
# 2. Pulls latest code
# 3. Rebuilds container
# 4. Runs health checks
# 5. Deploys with zero downtime
# 6. Sends notification
```

**Time:** ~3-5 minutes per deployment

### Manual Deployments

**If needed:**
1. Go to App Platform
2. Click "Actions" → "Force Rebuild and Deploy"
3. Confirm

**Use cases:**
- Environment variable changes
- Force rebuild after failed deployment
- Rollback to previous version

---

## 🔧 Configuration Updates

### Update Environment Variables

**Time:** ~2 minutes + redeployment (3-5 min)

1. **In App Platform:**
   - Settings → Environment Variables
   - Edit existing or add new variables
   - Click "Save"

2. **Triggers Automatic Redeployment**
   - New variables available in ~5 minutes

### Example: Update LLM API Key

```bash
# In App Platform dashboard:
# 1. Settings → Environment Variables
# 2. Find LLM_API_KEY
# 3. Click Edit
# 4. Update value
# 5. Save (triggers redeploy)
```

---

## 📈 Scaling

### Horizontal Auto-Scaling (Included)

**App Platform automatically scales:**
- Monitors request rate
- Adds containers when traffic increases
- Removes containers when traffic decreases
- Load balances between containers

**Configuration:**
1. Settings → Professional Plan Features
2. Enable "Autoscaling"
3. Set min/max containers:
   - Min: 1 container (always running)
   - Max: 3 containers (scales up to 3)

**Cost:** Pay per container-second (only when scaled up)

### Vertical Scaling

**Upgrade plan:**
1. Settings → App Spec
2. Change instance size
3. Save (triggers redeploy)

**Options:**
- Basic: 512MB RAM ($5/month)
- Professional: 1GB RAM ($12/month)
- Professional: 2GB RAM ($24/month)
- Professional: 4GB RAM ($48/month)

---

## 🔒 Security Features (Built-in)

**Automatic Security:**
- ✅ **SSL/TLS Certificates** - Free, auto-renewing
- ✅ **DDoS Protection** - Built into platform
- ✅ **Web Application Firewall (WAF)** - Available with Pro plan
- ✅ **Container Isolation** - Secure by default
- ✅ **Secret Management** - Encrypted environment variables
- ✅ **HTTPS Only** - Enforced by default

**Additional Security:**

1. **Enable WAF (Recommended):**
   - Settings → Security
   - Enable "Web Application Firewall"
   - Protects against OWASP Top 10

2. **IP Allowlisting (Optional):**
   - Settings → Security
   - Add trusted IPs
   - Restrict access to specific IPs

3. **Rate Limiting:**
   - Already configured in Nginx (app-level)
   - Additional platform-level available

---

## 💡 Best Practices

### 1. Use Health Checks

**Already configured!** App Platform checks `/health` endpoint.

**Custom health check:**
```python
# In server/api/app.py
@app.get("/health")
async def health_check():
    # Check database connection
    # Check LLM API
    # Return status
    return {"status": "ok", "version": "1.0.0"}
```

### 2. Set Appropriate Timeouts

**In App Platform:**
- HTTP Request Timeout: 300 seconds (default)
- For LLM endpoints, may need longer

**Configure:**
```yaml
# .do/app.yaml (optional)
services:
- name: planly-backend
  http_port: 8000
  health_check:
    http_path: /health
  routes:
  - path: /
    timeout: 300s
```

### 3. Use Environment-Specific Configs

**Staging vs Production:**

**Option 1: Multiple Apps**
- Create `planly-backend-staging`
- Create `planly-backend-prod`
- Different environment variables

**Option 2: Branch-Based**
- `main` branch → Production
- `staging` branch → Staging
- App Platform deploys based on branch

### 4. Monitor Resource Usage

**Check regularly:**
- CPU/Memory usage trends
- Response times
- Error rates

**Upgrade if:**
- CPU > 80% consistently
- Memory near limit
- Response time increasing

---

## 🐛 Troubleshooting

### Build Failed

**Check build logs:**
1. App Platform → Activity
2. Click failed deployment
3. View build logs

**Common issues:**
- Missing dependency in requirements.txt
- Python version mismatch
- Import errors

**Fix:**
```bash
# Test locally first
cd server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Health Check Failed

**App shows "Unhealthy":**

**Check:**
1. Is `/health` endpoint working?
   ```bash
   curl https://your-app.ondigitalocean.app/health
   ```

2. Check runtime logs for errors

3. Verify environment variables set correctly

**Fix:**
- Ensure main.py runs on port 8000
- Check HOST=0.0.0.0 in .env
- Verify health endpoint returns 200 OK

### Database Connection Failed

**Error in logs: "Database connection failed"**

**Check:**
1. Verify SUPABASE_URL is correct
2. Verify SUPABASE_KEY is service_role key (not anon key)
3. Check database schema created
4. Test connection:
   ```bash
   curl https://your-app.ondigitalocean.app/health/db
   ```

**Fix:**
- Update environment variables in App Platform
- Redeploy application
- Run database schema if not already done

### Slow Response Times

**App responding slowly:**

**Check:**
1. Performance metrics in dashboard
2. CPU/Memory usage
3. Database query performance

**Solutions:**
- Upgrade to larger instance size
- Enable auto-scaling
- Optimize database queries
- Use caching (Redis)

### Out of Memory

**App crashes with OOM error:**

**Solutions:**
1. Upgrade to larger instance (2GB or 4GB)
2. Check for memory leaks in code
3. Reduce concurrent requests
4. Add memory monitoring

---

## 🔄 Rollback Deployment

**If deployment breaks:**

**Time:** ~2 minutes

1. **In App Platform:**
   - Go to Activity tab
   - Find previous successful deployment
   - Click "..." menu
   - Select "Rollback to this deployment"
   - Confirm

2. **Automatic rollback:**
   - Previous version deployed
   - Takes ~3 minutes
   - Zero downtime

---

## 📊 Cost Optimization

### Tips to Reduce Costs:

1. **Use Basic tier for development:**
   - $5/month during development
   - Upgrade to Professional for production

2. **Disable auto-scaling if not needed:**
   - Fixed 1 container = predictable costs
   - Enable only during high traffic periods

3. **Use Supabase free tier:**
   - 500MB database
   - 2GB bandwidth
   - Upgrade only when needed

4. **Use Groq free tier:**
   - Generous free limits
   - Switch to paid only if rate limited

**Total minimum cost: $5/month (dev) or $12/month (prod)**

---

## ⏱️ Time Summary

| Step | Task | Time |
|------|------|------|
| 0 | Prerequisites (accounts, git push) | 10 min |
| 1 | Create App & Connect GitHub | 3 min |
| 2 | Configure Environment Variables | 5 min |
| 3 | Select Plan | 1 min |
| 4 | Wait for Deployment (automatic) | 5 min |
| 5 | Configure Database (Supabase) | 3 min |
| 6 | Add Custom Domain (optional) | 5 min |
| 7 | Testing | 3 min |

**Total Active Time:** 20 minutes (30 min with custom domain)

**vs Droplet Deployment:** 40 minutes

**Time Saved:** 20 minutes + much easier management!

---

## 📝 Deployment Checklist

**Pre-Deployment:**
- [ ] Code pushed to GitHub/GitLab
- [ ] `requirements.txt` up to date
- [ ] Supabase project created
- [ ] Cloud LLM API key obtained
- [ ] DigitalOcean account ready

**Deployment:**
- [ ] App created in App Platform
- [ ] GitHub connected and authorized
- [ ] Build/run commands configured
- [ ] All environment variables set
- [ ] Plan selected (Professional recommended)
- [ ] Initial deployment successful
- [ ] Database schema executed
- [ ] Health check passing

**Post-Deployment:**
- [ ] All endpoints tested
- [ ] Documentation updated with app URL
- [ ] Monitoring alerts configured
- [ ] Auto-deployment verified
- [ ] Team notified
- [ ] Performance baseline recorded

**Optional:**
- [ ] Custom domain added
- [ ] WAF enabled
- [ ] Auto-scaling configured
- [ ] Staging environment created

---

## 🆚 App Platform vs Droplet Comparison

| Feature | Droplet | App Platform |
|---------|---------|--------------|
| **Setup Time** | 40 minutes | 20 minutes |
| **Server Management** | Manual SSH, updates | Automatic |
| **SSL Setup** | Manual Certbot | Automatic |
| **Scaling** | Manual resize | Auto-scaling |
| **Zero-Downtime Deploy** | Complex setup | Built-in |
| **Monitoring** | Setup required | Built-in dashboard |
| **Log Management** | Manual setup | Built-in logs |
| **Cost (1GB)** | $6-12/month | $12/month |
| **Learning Curve** | Higher | Lower |
| **Flexibility** | Full control | Some limitations |
| **Best For** | DevOps experience, custom needs | Quick deployment, simplicity |

---

## 🎉 Success!

Your Planly backend is now live on DigitalOcean App Platform!

**Your App:**
- **URL:** https://planly-backend-xxxxx.ondigitalocean.app
- **Docs:** https://planly-backend-xxxxx.ondigitalocean.app/docs
- **Health:** https://planly-backend-xxxxx.ondigitalocean.app/health

**What You Got:**
- ✅ Auto-scaling infrastructure
- ✅ Free SSL/HTTPS
- ✅ CI/CD from GitHub
- ✅ Zero-downtime deployments
- ✅ Built-in monitoring
- ✅ DDoS protection
- ✅ Automatic health checks

**Next Steps:**
1. Update Agent 2 (Desktop + Telegram) with app URL
2. Test end-to-end flows
3. Set up staging environment (optional)
4. Configure auto-scaling if needed
5. Monitor metrics in dashboard

**Support:**
- DigitalOcean App Platform Docs: https://docs.digitalocean.com/products/app-platform/
- Planly API Docs: `API_SPECIFICATION.md`
- Community: DigitalOcean Community Forums

---

## 💡 Pro Tips

### 1. Use `.do/app.yaml` for Advanced Config

Create `.do/app.yaml` in repository root:

```yaml
name: planly-backend
services:
- name: web
  github:
    repo: yourusername/planly
    branch: main
    deploy_on_push: true
  source_dir: /server
  http_port: 8000
  instance_count: 1
  instance_size_slug: professional-xs
  health_check:
    http_path: /health
    initial_delay_seconds: 60
    period_seconds: 10
    timeout_seconds: 5
    success_threshold: 1
    failure_threshold: 3
  routes:
  - path: /
  envs:
  - key: PORT
    value: "8000"
  # Other env vars in dashboard for security
```

### 2. Set Up Staging Branch

```bash
# Create staging branch
git checkout -b staging
git push -u origin staging

# In App Platform:
# Create new app "planly-backend-staging"
# Connect to 'staging' branch
# Different environment variables for testing
```

### 3. Use GitHub Actions for Pre-Deploy Tests

```yaml
# .github/workflows/test.yml
name: Test

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.12'
    - name: Install dependencies
      run: |
        cd server
        pip install -r requirements.txt
    - name: Run tests
      run: |
        cd server
        pytest tests/
```

### 4. Monitor Costs

**Set Budget Alerts:**
1. Billing → Budgets
2. Create alert for $20/month
3. Get notified before costs spike

---

**Deployed by:** Agent 1 Team
**Platform:** DigitalOcean App Platform
**Deployment Date:** 2026-02-09
**Status:** ✅ Production Ready
**Deployment Method:** Git-based CI/CD
