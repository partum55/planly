# Google OAuth Setup Guide

**Complete guide to enable "Continue with Google" login**

**Time Estimate:** 10-15 minutes

**Last Updated:** 2026-02-09

---

## 📋 What is Google OAuth?

Google OAuth allows users to login to Planly using their Google account instead of creating a new password. This provides:

- ✅ **Better UX** - Users don't need to remember another password
- ✅ **Faster signup** - One click to create account
- ✅ **More secure** - Google handles authentication
- ✅ **Trusted** - Users trust Google login

**Use Case:** Desktop app "Continue with Google" button

---

## 🎯 Prerequisites

Before starting:
- [ ] Google account (personal or workspace)
- [ ] Access to Google Cloud Console
- [ ] Planly server .env file access

**No credit card required** - Google OAuth is free!

---

## 🚀 Step-by-Step Setup

### Step 1: Create Google Cloud Project (3 minutes)

**Time:** ~3 minutes

1. **Go to Google Cloud Console:**
   - Visit: https://console.cloud.google.com/
   - Sign in with your Google account

2. **Create New Project:**
   - Click project dropdown (top left, near "Google Cloud")
   - Click "NEW PROJECT"

   **Project Details:**
   - **Project name:** `Planly`
   - **Organization:** Leave default (No organization)
   - Click "CREATE"

3. **Wait for Project Creation:**
   - Takes ~30 seconds
   - You'll see notification when ready
   - Select the new project from dropdown

---

### Step 2: Enable Google+ API (2 minutes)

**Time:** ~2 minutes

**Why?** OAuth needs access to user profile information

1. **In Google Cloud Console:**
   - Make sure "Planly" project is selected
   - Go to: **APIs & Services** → **Library**
   - Or visit: https://console.cloud.google.com/apis/library

2. **Search for APIs:**
   - In search bar, type: `Google+ API`
   - Click "Google+ API" result
   - Click "ENABLE" button

3. **Also Enable (Optional but recommended):**
   - Search: `People API`
   - Click "People API"
   - Click "ENABLE"

**Note:** These APIs are free for OAuth use

---

### Step 3: Configure OAuth Consent Screen (5 minutes)

**Time:** ~5 minutes

**Important:** This is what users see when they click "Continue with Google"

1. **Go to OAuth Consent Screen:**
   - **APIs & Services** → **OAuth consent screen**
   - Or visit: https://console.cloud.google.com/apis/credentials/consent

2. **Choose User Type:**
   - **For Development/Testing:** Select "External"
   - Click "CREATE"

   **External vs Internal:**
   - **External:** Anyone with Google account can login (recommended)
   - **Internal:** Only your Google Workspace users (if you have workspace)

3. **Fill App Information:**

   **App Information:**
   - **App name:** `Planly`
   - **User support email:** Your email (select from dropdown)
   - **App logo:** (Optional - can skip for now)

   **App Domain (Optional for testing):**
   - **Application home page:** `http://localhost:8000` (for development)
   - **Privacy policy:** (Can skip for testing)
   - **Terms of service:** (Can skip for testing)

   **Developer Contact Information:**
   - **Email addresses:** Your email

   Click "SAVE AND CONTINUE"

4. **Scopes:**
   - Click "ADD OR REMOVE SCOPES"

   **Select these scopes:**
   - ✅ `openid`
   - ✅ `email` (under "Google OAuth2 API v2")
   - ✅ `profile` (under "Google OAuth2 API v2")

   Click "UPDATE" → "SAVE AND CONTINUE"

5. **Test Users (For development):**
   - Click "ADD USERS"
   - Add your email and any team members' emails
   - Click "ADD" → "SAVE AND CONTINUE"

   **Note:** In testing mode, only these users can login
   **For production:** You'll need to submit for verification (or stay in testing for hackathon)

6. **Summary:**
   - Review information
   - Click "BACK TO DASHBOARD"

---

### Step 4: Create OAuth Credentials (3 minutes)

**Time:** ~3 minutes

**This is where you get Client ID and Client Secret**

1. **Go to Credentials:**
   - **APIs & Services** → **Credentials**
   - Or visit: https://console.cloud.google.com/apis/credentials

2. **Create OAuth Client ID:**
   - Click "CREATE CREDENTIALS" (top)
   - Select "OAuth client ID"

3. **Configure OAuth Client:**

   **Application type:**
   - Select "Web application"

   **Name:**
   - Enter: `Planly Desktop App`

   **Authorized JavaScript origins (Optional):**
   - Add: `http://localhost:8000`
   - Add: `https://yourdomain.com` (if you have production domain)

   **Authorized redirect URIs:**
   - Add: `http://localhost:8000/auth/google/callback`
   - Add: `https://yourdomain.com/auth/google/callback` (if production)

   **Important:** The redirect URI must match exactly what your app uses!

   Click "CREATE"

4. **Save Your Credentials:**
   - A popup appears with your credentials
   - **Client ID:** Looks like `123456789-abcdefgh.apps.googleusercontent.com`
   - **Client Secret:** Looks like `GOCSPX-abcdefghijklmnop`

   **⚠️ IMPORTANT:** Copy these now! You'll need them in the next step.

   **Download JSON (Optional):**
   - You can also download the JSON file for backup
   - Click "DOWNLOAD JSON"
   - Keep it secure (don't commit to git!)

---

### Step 5: Add Credentials to Server (2 minutes)

**Time:** ~2 minutes

1. **Open Server .env File:**
   ```bash
   cd /path/to/planly/server
   nano .env
   # or
   code .env
   ```

2. **Add OAuth Credentials:**
   ```bash
   # Google OAuth (for desktop app "Continue with Google")
   GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-your-client-secret-here
   ```

   **Replace with actual values from Step 4**

3. **Save File:**
   - Ctrl+O, Enter, Ctrl+X (nano)
   - Or just save (VS Code)

4. **Restart Server:**
   ```bash
   # If running locally
   # Stop with Ctrl+C, then:
   venv/bin/python main.py

   # If using systemd
   sudo systemctl restart planly

   # If on App Platform
   # Commit changes and push:
   git add server/.env
   git commit -m "Add Google OAuth credentials"
   git push origin main
   # (App Platform will auto-deploy)
   ```

---

## 🧪 Testing OAuth Flow

### Test 1: Verify Endpoint Exists

```bash
# Check if OAuth endpoint is accessible
curl http://localhost:8000/docs

# Look for: POST /auth/google/callback
```

### Test 2: Manual OAuth Flow (Advanced)

**Step-by-step test:**

1. **Get Authorization URL:**
   ```
   https://accounts.google.com/o/oauth2/v2/auth?
   client_id=YOUR_CLIENT_ID&
   redirect_uri=http://localhost:8000/auth/google/callback&
   response_type=code&
   scope=openid%20email%20profile&
   access_type=offline
   ```

   Replace `YOUR_CLIENT_ID` with your actual Client ID

2. **Open in Browser:**
   - Paste URL in browser
   - Select Google account
   - Click "Allow"
   - You'll be redirected to: `http://localhost:8000/auth/google/callback?code=4/0AX4XfWh...`

3. **Extract Code:**
   - Copy the `code` parameter value from URL
   - Example: `4/0AX4XfWh_abc123...`

4. **Test Backend Endpoint:**
   ```bash
   curl -X POST http://localhost:8000/auth/google/callback \
     -H "Content-Type: application/json" \
     -d '{"code": "4/0AX4XfWh_your_code_here"}'
   ```

   **Expected Response:**
   ```json
   {
     "user_id": "uuid-string",
     "access_token": "jwt...",
     "refresh_token": "jwt..."
   }
   ```

### Test 3: Desktop App Integration

**In your desktop app:**

```javascript
// Example: Electron app
const { BrowserWindow } = require('electron');

async function loginWithGoogle() {
  const authWindow = new BrowserWindow({
    width: 500,
    height: 600,
    webPreferences: {
      nodeIntegration: false
    }
  });

  const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
    `client_id=${CLIENT_ID}&` +
    `redirect_uri=http://localhost:8000/auth/google/callback&` +
    `response_type=code&` +
    `scope=openid email profile&` +
    `access_type=offline`;

  authWindow.loadURL(authUrl);

  // Listen for redirect
  authWindow.webContents.on('will-redirect', async (event, url) => {
    const urlParams = new URL(url);
    const code = urlParams.searchParams.get('code');

    if (code) {
      authWindow.close();

      // Send code to your backend
      const response = await fetch('http://localhost:8000/auth/google/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
      });

      const data = await response.json();
      // Save tokens: data.access_token, data.refresh_token
      console.log('Logged in:', data.user_id);
    }
  });
}
```

---

## 🔧 Server Implementation Details

### OAuth Endpoint (Already Implemented!)

**File:** `server/api/routes/auth.py`

```python
@router.post("/google/callback", response_model=TokenResponse)
async def google_oauth_callback(request: GoogleOAuthCallbackRequest):
    """
    Google OAuth callback

    Flow:
    1. Desktop app opens Google consent page
    2. User approves
    3. Desktop app captures authorization code
    4. Desktop app POSTs code to this endpoint
    5. Backend exchanges code for Google access token
    6. Backend fetches user info from Google
    7. Backend creates/finds user in database
    8. Backend returns JWT tokens
    """
    try:
        # Exchange code for Google access token
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": request.code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": "http://localhost:8000/auth/google/callback",
            "grant_type": "authorization_code"
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=token_data)
            tokens = token_response.json()

            # Fetch user info from Google
            userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            userinfo_response = await client.get(userinfo_url, headers=headers)
            user_info = userinfo_response.json()

        # Find or create user by email
        user = await user_repo.get_user_by_email(user_info['email'])

        if not user:
            # Create new user (no password for OAuth users)
            user, access_token, refresh_token = await auth_service.register_user(
                email=user_info['email'],
                password=None,
                full_name=user_info.get('name')
            )
        else:
            # Existing user - generate tokens
            access_token, refresh_token = await auth_service.generate_tokens(user['id'])

        return TokenResponse(
            user_id=str(user['id']),
            access_token=access_token,
            refresh_token=refresh_token
        )

    except Exception as e:
        logger.error(f"Google OAuth error: {e}")
        raise HTTPException(status_code=400, detail="OAuth authentication failed")
```

**Already implemented in your server!** ✅

---

## 🔒 Security Best Practices

### 1. Keep Client Secret Secure

**DO:**
- ✅ Store in `.env` file
- ✅ Add `.env` to `.gitignore`
- ✅ Use environment variables in production
- ✅ Rotate secret if compromised

**DON'T:**
- ❌ Commit to git
- ❌ Share in public channels
- ❌ Hard-code in source files
- ❌ Include in frontend code

### 2. Validate Redirect URIs

**In Google Cloud Console:**
- Only add URIs you control
- Use HTTPS in production
- Be specific (no wildcards)

**Example:**
- ✅ `https://api.yourdomain.com/auth/google/callback`
- ❌ `https://*.yourdomain.com/callback`

### 3. Use State Parameter (Optional but Recommended)

Prevents CSRF attacks:

```python
# Generate state token
state = secrets.token_urlsafe(32)
# Store in session
session['oauth_state'] = state

# Add to auth URL
auth_url = f"...&state={state}"

# Verify in callback
if request.state != session.get('oauth_state'):
    raise Exception("Invalid state parameter")
```

### 4. Token Storage (Desktop App)

**Best practices:**
- Use secure storage (Keychain on Mac, Credential Manager on Windows)
- Don't store in localStorage (web apps)
- Encrypt if storing in files
- Clear on logout

---

## 🌐 Production Deployment

### Update Redirect URIs for Production

**When deploying to production:**

1. **Go to Google Cloud Console:**
   - Credentials → Your OAuth Client
   - Click "Edit"

2. **Add Production URIs:**
   - **Authorized redirect URIs:**
     - Add: `https://api.yourdomain.com/auth/google/callback`
     - Keep: `http://localhost:8000/auth/google/callback` (for local dev)

3. **Update Server .env:**
   ```bash
   # Production
   GOOGLE_CLIENT_ID=same-as-before
   GOOGLE_CLIENT_SECRET=same-as-before
   ```

4. **Update Desktop App:**
   - Change redirect_uri in OAuth URL to production URL
   - Or make it configurable based on environment

### Publishing OAuth App (Optional)

**For public use beyond 100 test users:**

1. **Complete Verification:**
   - Go to OAuth consent screen
   - Click "PUBLISH APP"
   - Google will review your app (1-2 weeks)

2. **Requirements:**
   - Privacy policy URL
   - Terms of service URL
   - App homepage
   - Verified domain

3. **For Hackathon:**
   - Stay in "Testing" mode
   - Add all team members as test users
   - No verification needed

---

## 🐛 Troubleshooting

### Error: "redirect_uri_mismatch"

**Problem:** Redirect URI doesn't match Google Console configuration

**Solution:**
1. Check exact URI in Google Console
2. Must match exactly (including http vs https, trailing slash)
3. Update in Google Console if needed

**Example Fix:**
```bash
# If error shows:
# redirect_uri: http://localhost:8000/auth/google/callback
#
# Make sure Google Console has exact same URI
```

### Error: "invalid_client"

**Problem:** Client ID or Secret is wrong

**Solution:**
1. Verify `GOOGLE_CLIENT_ID` in `.env` matches Console
2. Verify `GOOGLE_CLIENT_SECRET` in `.env` matches Console
3. No extra spaces or quotes
4. Restart server after changing

### Error: "access_denied"

**Problem:** User clicked "Cancel" or isn't a test user

**Solution:**
1. Add user as test user in OAuth consent screen
2. User needs to actually click "Allow"
3. Check consent screen shows correct app name

### Error: "invalid_grant"

**Problem:** Authorization code expired or already used

**Solution:**
1. Codes expire in ~10 minutes
2. Each code can only be used once
3. Get a fresh code and try again

### Backend Error: "Invalid authorization code"

**Problem:** Code exchange failed

**Check:**
1. `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are correct
2. Redirect URI matches exactly
3. Code is recent (not expired)
4. Server can reach Google APIs (not blocked by firewall)

**Debug:**
```bash
# Check server logs
tail -f /var/log/planly/error.log

# Or if running locally:
# Check console output for detailed error
```

---

## 📊 Testing Checklist

**Before launching:**

- [ ] Google Cloud project created
- [ ] OAuth consent screen configured
- [ ] OAuth credentials created
- [ ] Client ID and Secret added to `.env`
- [ ] Server restarted with new credentials
- [ ] Test users added (if in testing mode)
- [ ] Redirect URIs match exactly
- [ ] Manual OAuth flow works
- [ ] Backend `/auth/google/callback` returns tokens
- [ ] User created in database
- [ ] Desktop app integration works
- [ ] Tokens saved in desktop app
- [ ] User can access protected endpoints with token

---

## 💡 Tips & Tricks

### 1. Multiple Environments

**Development vs Production:**

```bash
# Development .env
GOOGLE_CLIENT_ID=dev-client-id
GOOGLE_CLIENT_SECRET=dev-secret

# Production .env
GOOGLE_CLIENT_ID=prod-client-id
GOOGLE_CLIENT_SECRET=prod-secret
```

Create separate OAuth clients for each environment!

### 2. Desktop App Dynamic Redirect

```javascript
// Desktop app - auto-detect environment
const isDev = process.env.NODE_ENV === 'development';
const redirectUri = isDev
  ? 'http://localhost:8000/auth/google/callback'
  : 'https://api.yourdomain.com/auth/google/callback';
```

### 3. Better User Experience

**Auto-close OAuth window:**
```javascript
// After successful login
authWindow.close();
mainWindow.webContents.send('login-success', userData);
```

**Remember user:**
```javascript
// Save user preference
localStorage.setItem('preferred_login', 'google');

// Show Google login first if preferred
if (localStorage.getItem('preferred_login') === 'google') {
  showGoogleLoginButton();
}
```

### 4. Error Handling

**In desktop app:**
```javascript
try {
  const response = await fetch('/auth/google/callback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code })
  });

  if (!response.ok) {
    throw new Error('OAuth failed');
  }

  const data = await response.json();
  // Success!

} catch (error) {
  console.error('Google login failed:', error);
  showErrorMessage('Google login failed. Please try again.');
}
```

---

## 📚 Additional Resources

**Google Documentation:**
- OAuth 2.0: https://developers.google.com/identity/protocols/oauth2
- Sign-In: https://developers.google.com/identity/sign-in/web
- User Info: https://developers.google.com/identity/protocols/oauth2/openid-connect

**Testing Tools:**
- OAuth Playground: https://developers.google.com/oauthplayground
- JWT Decoder: https://jwt.io

**Planly Documentation:**
- API Specification: `API_SPECIFICATION.md`
- Backend Implementation: `server/api/routes/auth.py`

---

## ⏱️ Time Summary

| Step | Task | Time |
|------|------|------|
| 1 | Create Google Cloud Project | 3 min |
| 2 | Enable APIs | 2 min |
| 3 | Configure OAuth Consent Screen | 5 min |
| 4 | Create OAuth Credentials | 3 min |
| 5 | Add Credentials to Server | 2 min |
| - | **Testing** | 3 min |

**Total Time: 15 minutes**

**One-time setup** - Then works forever!

---

## 🎉 Success!

Your Planly server now supports Google OAuth!

**What Users See:**
1. Click "Continue with Google" in desktop app
2. Google login page opens
3. Select account
4. Grant permissions
5. Automatically logged into Planly

**What Happens Behind the Scenes:**
1. Desktop app opens Google consent
2. User approves
3. Desktop app gets authorization code
4. Desktop app sends code to your backend
5. Backend exchanges code for Google tokens
6. Backend gets user info from Google
7. Backend creates user (if new) or finds existing
8. Backend returns Planly JWT tokens
9. Desktop app stores tokens
10. User is authenticated!

**Next Steps:**
1. Integrate with desktop app frontend
2. Add "Continue with Google" button
3. Test with team members
4. Add error handling
5. Consider adding other OAuth providers (GitHub, Microsoft)

---

**Setup by:** Agent 1 Team
**Last Updated:** 2026-02-09
**Status:** ✅ Ready for Integration
**Backend Support:** Fully Implemented
