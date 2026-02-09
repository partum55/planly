# Planly Deployment Guide: DigitalOcean

**Complete deployment guide with time estimates for each step**

**Total Time Estimate:** 25-35 minutes (excluding DNS propagation)

**Last Updated:** 2026-02-09

---

## 📋 Prerequisites

Before starting, have ready:
- [ ] DigitalOcean account ([Sign up here](https://www.digitalocean.com/))
- [ ] Domain name (optional, but recommended)
- [ ] Supabase project credentials
- [ ] Cloud LLM API key (Groq, Together AI, or OpenRouter)
- [ ] Local git repository with latest code

**Setup Time:** 5-10 minutes if you need to create accounts

---

## 🚀 Deployment Steps

### Step 1: Create Droplet (5 minutes)

**Time:** ~5 minutes

1. **Log into DigitalOcean**
   - Go to https://cloud.digitalocean.com/
   - Click "Create" → "Droplets"

2. **Choose Configuration:**
   - **Image:** Ubuntu 24.04 LTS
   - **Plan:** Basic
   - **CPU Options:** Regular (Shared CPU)
   - **Size:** $6/month plan (1GB RAM, 1 vCPU, 25GB SSD)
     - Sufficient for hackathon/demo
     - For production: $12/month (2GB RAM) recommended

3. **Datacenter Region:**
   - Choose closest to your users
   - Example: New York (NYC1) for US East Coast

4. **Authentication:**
   - **Recommended:** SSH Key
   - **Alternative:** Password (less secure)

   If using SSH key:
   ```bash
   # Generate SSH key locally (if you don't have one)
   ssh-keygen -t ed25519 -C "your_email@example.com"

   # Display public key
   cat ~/.ssh/id_ed25519.pub

   # Copy and paste into DigitalOcean
   ```

5. **Finalize:**
   - Hostname: `planly-backend`
   - Tags: `planly`, `production`
   - Click "Create Droplet"

**Wait:** 30-60 seconds for droplet creation

**Result:** You'll receive droplet IP address (e.g., 167.99.123.45)

---

### Step 2: Initial Server Setup (5 minutes)

**Time:** ~5 minutes

1. **Connect to Droplet:**
   ```bash
   # Replace with your droplet IP
   ssh root@167.99.123.45
   ```

2. **Update System:**
   ```bash
   apt update && apt upgrade -y
   ```
   **Time:** 2-3 minutes

3. **Install Required Packages:**
   ```bash
   # Python and build tools
   apt install -y python3.12 python3.12-venv python3-pip git nginx certbot python3-certbot-nginx

   # Node.js (for potential future use)
   curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
   apt install -y nodejs
   ```
   **Time:** 2 minutes

4. **Create Application User:**
   ```bash
   # Create non-root user for security
   adduser planly --disabled-password --gecos ""
   usermod -aG sudo planly

   # Switch to planly user
   su - planly
   ```

---

### Step 3: Deploy Application (8 minutes)

**Time:** ~8 minutes

1. **Clone Repository:**
   ```bash
   cd /home/planly

   # Option A: From GitHub (if pushed)
   git clone https://github.com/your-username/planly.git

   # Option B: Upload via SCP (from local machine)
   # On your local machine:
   # scp -r /path/to/planly planly@167.99.123.45:/home/planly/

   cd planly
   ```
   **Time:** 1-2 minutes depending on connection

2. **Create Virtual Environment:**
   ```bash
   cd server
   python3.12 -m venv venv
   source venv/bin/activate
   ```
   **Time:** 30 seconds

3. **Install Python Dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
   **Time:** 3-4 minutes

4. **Configure Environment:**
   ```bash
   # Copy template
   cp .env.template .env

   # Edit configuration
   nano .env
   ```

   **Set these values:**
   ```bash
   # Database
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your_service_role_key

   # LLM (use Groq for free tier)
   USE_CLOUD_LLM=true
   OLLAMA_ENDPOINT=https://api.groq.com/openai
   OLLAMA_MODEL=llama-3.1-8b-instant
   LLM_API_KEY=your_groq_api_key

   # Server
   HOST=127.0.0.1  # Important: bind to localhost only
   PORT=8000
   LOG_LEVEL=INFO

   # JWT Secret (generate secure one)
   JWT_SECRET_KEY=$(openssl rand -base64 32)
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   REFRESH_TOKEN_EXPIRE_DAYS=30

   # Optional: Google OAuth
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret

   # Context
   CONTEXT_WINDOW_MINUTES=60
   ```

   **Save:** Ctrl+O, Enter, Ctrl+X
   **Time:** 2 minutes

5. **Test Server:**
   ```bash
   # Quick test
   venv/bin/python main.py

   # In another terminal:
   curl http://localhost:8000/health
   # Should return: {"status":"ok"}

   # Stop server: Ctrl+C
   ```
   **Time:** 1 minute

---

### Step 4: Setup Systemd Service (3 minutes)

**Time:** ~3 minutes

1. **Create Service File:**
   ```bash
   sudo nano /etc/systemd/system/planly.service
   ```

2. **Add Configuration:**
   ```ini
   [Unit]
   Description=Planly AI Agent Backend
   After=network.target

   [Service]
   Type=simple
   User=planly
   WorkingDirectory=/home/planly/planly/server
   Environment="PATH=/home/planly/planly/server/venv/bin"
   ExecStart=/home/planly/planly/server/venv/bin/python main.py
   Restart=always
   RestartSec=10
   StandardOutput=append:/var/log/planly/access.log
   StandardError=append:/var/log/planly/error.log

   [Install]
   WantedBy=multi-user.target
   ```

   **Save:** Ctrl+O, Enter, Ctrl+X

3. **Create Log Directory:**
   ```bash
   sudo mkdir -p /var/log/planly
   sudo chown planly:planly /var/log/planly
   ```

4. **Enable and Start Service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable planly
   sudo systemctl start planly

   # Check status
   sudo systemctl status planly
   ```

   **Expected:** Active (running) in green

5. **View Logs:**
   ```bash
   # Real-time logs
   sudo journalctl -u planly -f

   # Recent logs
   sudo tail -50 /var/log/planly/error.log
   ```

---

### Step 5: Configure Nginx Reverse Proxy (4 minutes)

**Time:** ~4 minutes

1. **Create Nginx Configuration:**
   ```bash
   sudo nano /etc/nginx/sites-available/planly
   ```

2. **Add Configuration:**
   ```nginx
   # HTTP configuration (will redirect to HTTPS after SSL setup)
   server {
       listen 80;
       server_name api.yourdomain.com;  # Change to your domain or IP

       # Rate limiting
       limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
       limit_req zone=api_limit burst=20 nodelay;

       # Security headers
       add_header X-Frame-Options "SAMEORIGIN" always;
       add_header X-Content-Type-Options "nosniff" always;
       add_header X-XSS-Protection "1; mode=block" always;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           proxy_cache_bypass $http_upgrade;

           # Timeouts
           proxy_connect_timeout 60s;
           proxy_send_timeout 60s;
           proxy_read_timeout 60s;
       }

       # Health check endpoint (no rate limit)
       location /health {
           proxy_pass http://127.0.0.1:8000/health;
           access_log off;
       }
   }
   ```

   **Save:** Ctrl+O, Enter, Ctrl+X

3. **Enable Site:**
   ```bash
   sudo ln -s /etc/nginx/sites-available/planly /etc/nginx/sites-enabled/
   sudo nginx -t  # Test configuration
   sudo systemctl restart nginx
   ```

4. **Test Access:**
   ```bash
   # From your local machine
   curl http://167.99.123.45/health
   # Should return: {"status":"ok"}
   ```

---

### Step 6: SSL/HTTPS Setup (3 minutes)

**Time:** ~3 minutes (+ DNS propagation if needed)

**Prerequisites:** Domain pointed to droplet IP

1. **Point Domain to Droplet:**
   - In your domain registrar (GoDaddy, Namecheap, etc.)
   - Create A record: `api.yourdomain.com` → `167.99.123.45`
   - **Wait:** 5-60 minutes for DNS propagation

2. **Install SSL Certificate:**
   ```bash
   sudo certbot --nginx -d api.yourdomain.com
   ```

   **Prompts:**
   - Email: your@email.com
   - Terms: Agree (A)
   - Redirect HTTP to HTTPS: Yes (2)

   **Time:** 1 minute

   **Result:** Certificate installed, auto-renewal configured

3. **Test HTTPS:**
   ```bash
   curl https://api.yourdomain.com/health
   ```

4. **Verify Auto-Renewal:**
   ```bash
   sudo certbot renew --dry-run
   ```

---

### Step 7: Firewall Configuration (2 minutes)

**Time:** ~2 minutes

1. **Setup UFW (Uncomplicated Firewall):**
   ```bash
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow ssh
   sudo ufw allow 'Nginx Full'
   sudo ufw enable

   # Check status
   sudo ufw status
   ```

2. **Expected Output:**
   ```
   Status: active

   To                         Action      From
   --                         ------      ----
   22/tcp                     ALLOW       Anywhere
   Nginx Full                 ALLOW       Anywhere
   ```

---

### Step 8: Database Setup (5 minutes)

**Time:** ~5 minutes (in Supabase dashboard)

1. **Run Database Schema:**
   - Go to Supabase dashboard: https://app.supabase.com/
   - Select your project
   - Go to SQL Editor (left sidebar)
   - Click "New Query"
   - Copy contents of `server/database/supabase_schema.sql`
   - Paste and click "Run"

   **Time:** 2 minutes

2. **Verify Tables Created:**
   - Go to Table Editor
   - Should see 7 tables: users, user_sessions, conversations, messages, events, agent_actions, desktop_screenshots

3. **Test Database Connection:**
   ```bash
   curl https://api.yourdomain.com/health/db
   ```

   **Expected:** All tables exist, schema_ready: true

---

## 🧪 Testing Deployment (5 minutes)

**Time:** ~5 minutes

### 1. Health Checks
```bash
# Basic health
curl https://api.yourdomain.com/health

# Database health
curl https://api.yourdomain.com/health/db

# API documentation
open https://api.yourdomain.com/docs
```

### 2. Registration Test
```bash
curl -X POST https://api.yourdomain.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "full_name": "Test User"
  }'
```

**Expected:** JSON with access_token and user_id

### 3. Login Test
```bash
curl -X POST https://api.yourdomain.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

### 4. Agent Processing Test
```bash
# Save access token from registration/login
TOKEN="your_access_token_here"

curl -X POST https://api.yourdomain.com/agent/process \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "user_prompt": "Schedule dinner tomorrow at 7pm",
    "source": "desktop_screenshot",
    "context": {
      "messages": [
        {"username":"Alice","text":"Dinner tomorrow?","timestamp":"2026-02-09T19:00:00Z"}
      ]
    }
  }'
```

**Expected:** JSON with blocks array

---

## 📊 Monitoring & Maintenance

### View Logs
```bash
# Application logs (real-time)
sudo journalctl -u planly -f

# Error logs
sudo tail -100 /var/log/planly/error.log

# Access logs
sudo tail -100 /var/log/planly/access.log

# Nginx logs
sudo tail -100 /var/log/nginx/access.log
sudo tail -100 /var/log/nginx/error.log
```

### Service Management
```bash
# Restart service
sudo systemctl restart planly

# Stop service
sudo systemctl stop planly

# Check status
sudo systemctl status planly

# View resource usage
top
htop  # if installed
```

### Update Application
```bash
cd /home/planly/planly
git pull origin main
cd server
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart planly
```

---

## 🔒 Security Checklist

- [ ] **SSH Key Authentication** - Disable password login
  ```bash
  sudo nano /etc/ssh/sshd_config
  # Set: PasswordAuthentication no
  sudo systemctl restart sshd
  ```

- [ ] **Firewall Enabled** - UFW configured correctly

- [ ] **SSL Certificate** - HTTPS enabled via Certbot

- [ ] **Environment Variables** - Secure secrets in .env

- [ ] **Database Access** - Use service_role key, not anon key

- [ ] **Rate Limiting** - Nginx configured with rate limits

- [ ] **Auto-Updates** - Enable unattended upgrades
  ```bash
  sudo apt install unattended-upgrades
  sudo dpkg-reconfigure --priority=low unattended-upgrades
  ```

- [ ] **Backups** - Setup automated backups (DigitalOcean Backups or Snapshots)

---

## 💰 Cost Breakdown

**Monthly Costs:**

| Service | Plan | Cost |
|---------|------|------|
| **DigitalOcean Droplet** | Basic 1GB | $6/month |
| **Supabase** | Free tier | $0/month |
| **Groq LLM** | Free tier | $0/month |
| **Domain Name** | varies | ~$12/year |
| **SSL Certificate** | Let's Encrypt | $0/month |

**Total:** ~$6/month + domain (~$1/month)

**For Production:**
- Droplet: $12/month (2GB RAM) recommended
- Supabase: Pro plan ($25/month) for higher limits
- Together AI: Pay as you go (~$5-20/month depending on usage)

---

## 📈 Scaling Options

### Option 1: Vertical Scaling (Easier)
**Upgrade droplet size:**
- $12/month: 2GB RAM, 1 vCPU
- $18/month: 2GB RAM, 2 vCPU
- $24/month: 4GB RAM, 2 vCPU

**Process:**
1. Power off droplet
2. Resize in DigitalOcean dashboard
3. Power on

**Time:** 5 minutes + downtime

### Option 2: Horizontal Scaling (More Complex)
**Use DigitalOcean App Platform:**
- Auto-scaling
- Load balancing
- Zero-downtime deployments
- Higher cost ($12-50/month)

### Option 3: Load Balancer
**Add multiple droplets:**
1. Create 2-3 identical droplets
2. Setup DigitalOcean Load Balancer ($12/month)
3. Distribute traffic

**Best for:** High traffic production

---

## 🚨 Troubleshooting

### Service Won't Start
```bash
# Check logs
sudo journalctl -u planly -n 50 --no-pager

# Check if port is in use
sudo lsof -i :8000

# Check environment
sudo -u planly cat /home/planly/planly/server/.env
```

### Database Connection Failed
```bash
# Test Supabase connection
curl https://your-project.supabase.co/rest/v1/

# Verify credentials in .env
grep SUPABASE /home/planly/planly/server/.env
```

### SSL Certificate Issues
```bash
# Renew manually
sudo certbot renew --force-renewal

# Check certificate status
sudo certbot certificates
```

### High Memory Usage
```bash
# Check memory
free -h

# Restart service
sudo systemctl restart planly

# Consider upgrading droplet
```

---

## ⏱️ Time Summary

| Step | Task | Time |
|------|------|------|
| 1 | Create Droplet | 5 min |
| 2 | Initial Server Setup | 5 min |
| 3 | Deploy Application | 8 min |
| 4 | Setup Systemd Service | 3 min |
| 5 | Configure Nginx | 4 min |
| 6 | SSL/HTTPS Setup | 3 min |
| 7 | Firewall Configuration | 2 min |
| 8 | Database Setup | 5 min |
| 9 | Testing | 5 min |

**Total Active Time:** 40 minutes

**Note:** DNS propagation (Step 6) can add 5-60 minutes of waiting time, but you can continue with other steps.

---

## 📝 Deployment Checklist

**Pre-Deployment:**
- [ ] Code pushed to git repository
- [ ] Supabase project created with credentials
- [ ] Cloud LLM API key obtained (Groq/Together AI)
- [ ] Domain name configured (optional)
- [ ] DigitalOcean account ready

**Deployment:**
- [ ] Droplet created and accessible
- [ ] System packages installed
- [ ] Application deployed and configured
- [ ] Systemd service running
- [ ] Nginx configured as reverse proxy
- [ ] SSL certificate installed (if using domain)
- [ ] Firewall configured
- [ ] Database schema executed
- [ ] All endpoints tested

**Post-Deployment:**
- [ ] Monitoring setup
- [ ] Backups configured
- [ ] Documentation updated with production URLs
- [ ] Team notified of deployment
- [ ] Performance baseline recorded

---

## 🎉 Success!

Your Planly backend is now live on DigitalOcean!

**Access Points:**
- **API:** https://api.yourdomain.com
- **Docs:** https://api.yourdomain.com/docs
- **Health:** https://api.yourdomain.com/health

**Next Steps:**
1. Update Agent 2 (Desktop + Telegram) with production API URL
2. Test end-to-end flows
3. Monitor logs for first few hours
4. Setup uptime monitoring (UptimeRobot, Pingdom)
5. Configure backups

**Support Resources:**
- DigitalOcean Docs: https://docs.digitalocean.com/
- Planly Docs: `API_SPECIFICATION.md`
- Community: DigitalOcean Community Forums

---

**Deployed by:** Agent 1 Team
**Deployment Date:** 2026-02-09
**Status:** ✅ Production Ready
