# How to Get Supabase Credentials

## Step-by-Step:

### 1. Project URL
- In your Supabase project dashboard
- Look at the URL in your browser
- It will be something like: `https://app.supabase.com/project/xxxxxxxxxxxxx`
- Your **Project URL** is: `https://xxxxxxxxxxxxx.supabase.co`
  - (Replace the x's with your actual project ID)

### 2. Service Role Key

**Important: We need the `service_role` key, NOT the `anon` key!**

1. In Supabase dashboard, click **"Settings"** (gear icon in sidebar)
2. Click **"API"** in the settings menu
3. Scroll down to **"Project API keys"** section
4. You'll see two keys:
   - `anon` / `public` - ❌ Don't use this one
   - `service_role` - ✅ **Use this one!**
5. Click the **"Copy"** button next to `service_role`
6. This is your **SUPABASE_KEY**

**⚠️ Security Warning:**
- The `service_role` key bypasses Row Level Security
- NEVER commit it to git or share it publicly
- Only use it in the backend server (never in frontend/mobile)
- It's already in `.gitignore`

### 3. Connection String (Optional)

If you need direct PostgreSQL access:

1. In **Settings** → **Database**
2. Scroll to **"Connection string"**
3. Choose **"URI"** tab
4. Copy the connection string
5. Replace `[YOUR-PASSWORD]` with your database password

This will be your **SUPABASE_DB_URL**

---

## Quick Checklist:

- [ ] Project URL: `https://xxxxx.supabase.co`
- [ ] Service Role Key: `eyJhbGc...` (long string starting with eyJ)
- [ ] Database Password: (the one you set during project creation)

## Next Steps:

1. Copy these credentials
2. Update `server/.env` file
3. Run the database schema (see next guide)
