# Auth0 Setup Guide for Tilli Master Chatbot

This guide walks you through setting up Auth0 as your identity provider for the Master Chatbot API.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Step 1: Create Auth0 Account](#step-1-create-auth0-account)
- [Step 2: Create an API in Auth0](#step-2-create-an-api-in-auth0)
- [Step 3: Configure Custom Claims](#step-3-configure-custom-claims)
- [Step 4: Configure Your Application](#step-4-configure-your-application)
- [Step 5: Test the Integration](#step-5-test-the-integration)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- An email address for Auth0 account creation
- Access to your Master Chatbot `.env` file
- Basic understanding of JWT tokens

---

## Step 1: Create Auth0 Account

1. **Go to Auth0**: Visit [https://auth0.com/signup](https://auth0.com/signup)

2. **Sign Up**:
   - Choose "Sign up" (free tier is sufficient for testing)
   - Use your work email or Google/Microsoft account
   - Select a **tenant domain** (e.g., `tilli-dev.us.auth0.com`)
     - This will be your `AUTH0_DOMAIN`
     - **Write this down!**

3. **Complete Setup**:
   - Choose your region (US, EU, AU)
   - Skip the "What are you building?" questions (or select "API")

---

## Step 2: Create an API in Auth0

1. **Navigate to APIs**:
   - In the Auth0 Dashboard, go to **Applications → APIs** (left sidebar)

2. **Create API**:
   - Click **"+ Create API"**
   - Fill in:
     - **Name**: `Tilli Master Chatbot API`
     - **Identifier**: `https://api.tilli.com/chatbot` (this is your `AUTH0_AUDIENCE`)
       - This can be any URL-like string (doesn't need to be a real URL)
       - **Write this down!**
     - **Signing Algorithm**: `RS256` (default, leave as-is)
   - Click **"Create"**

3. **Note Your Settings**:
   - You now have:
     - `AUTH0_DOMAIN`: `your-tenant.us.auth0.com`
     - `AUTH0_AUDIENCE`: `https://api.tilli.com/chatbot`

---

## Step 3: Configure Custom Claims

Auth0 tokens need to include `role` and `school_id` for our access control to work.

### 3.1: Create an Action (Auth0 Actions)

1. **Navigate to Actions**:
   - Go to **Actions → Flows** (left sidebar)
   - Select **"Login"**

2. **Create Custom Action**:
   - Click **"+"** (Custom tab)
   - Click **"Build from scratch"**
   - Fill in:
     - **Name**: `Add Tilli Claims`
     - **Trigger**: `Login / Post Login`
     - **Runtime**: `Node 18` (default)
   - Click **"Create"**

3. **Add Code**:
   Replace the default code with:

```javascript
/**
* Handler that will be called during the execution of a PostLogin flow.
*
* @param {Event} event - Details about the user and the context in which they are logging in.
* @param {PostLoginAPI} api - Interface whose methods can be used to change the behavior of the login.
*/
exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'https://tilli.com';
  
  // Get user metadata (you'll set this per user later)
  const role = event.user.app_metadata?.role || 'educator';
  const schoolId = event.user.app_metadata?.school_id || 'School 1';
  
  // Add custom claims to the token
  if (event.authorization) {
    api.idToken.setCustomClaim(`${namespace}/role`, role);
    api.idToken.setCustomClaim(`${namespace}/school_id`, schoolId);
    api.accessToken.setCustomClaim(`${namespace}/role`, role);
    api.accessToken.setCustomClaim(`${namespace}/school_id`, schoolId);
  }
};
```

4. **Deploy**:
   - Click **"Deploy"** (top right)

5. **Add to Login Flow**:
   - Go back to **Actions → Flows → Login**
   - Find your action "Add Tilli Claims" in the **Custom** tab (right sidebar)
   - **Drag and drop** it between "Start" and "Complete"
   - Click **"Apply"**

### 3.2: Set User Metadata (For Testing)

1. **Navigate to Users**:
   - Go to **User Management → Users** (left sidebar)

2. **Create a Test User** (or use existing):
   - Click **"+ Create User"**
   - Fill in:
     - **Email**: `test@tilli.com`
     - **Password**: (create a strong password)
     - **Connection**: `Username-Password-Authentication`
   - Click **"Create"**

3. **Add Metadata**:
   - Click on the user you just created
   - Scroll to **"Metadata"** section
   - Click **"app_metadata"** tab
   - Click **"Edit"** (pencil icon)
   - Add:
```json
{
  "role": "educator",
  "school_id": "School 1"
}
```
   - Click **"Save"**

> **Note**: In production, you would sync this metadata from your user database or set it during user registration.

---

## Step 4: Configure Your Application

### 4.1: Update `.env` File

Add these lines to your `.env` file (create it if it doesn't exist):

```bash
# Auth0 Configuration
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_AUDIENCE=https://api.tilli.com/chatbot

# Enable Authentication
ENABLE_AUTH=true
```

Replace `your-tenant.us.auth0.com` with your actual Auth0 domain.

### 4.2: Restart Your Server

```bash
# Stop the current server (Ctrl+C)
# Then restart:
.\start_server.ps1
```

---

## Step 5: Test the Integration

### 5.1: Get a Test Token

You need to get an access token from Auth0 to test the API.

**Option A: Use Auth0's Test Tool**

1. Go to **Applications → APIs** in Auth0 Dashboard
2. Click on your API (`Tilli Master Chatbot API`)
3. Go to **"Test"** tab
4. Click **"Copy Token"**
5. This token is valid for 24 hours

**Option B: Use a Script** (Recommended for repeated testing)

Create `scripts/get_auth0_token.py`:

```python
import requests
import os

# Auth0 Configuration
AUTH0_DOMAIN = "your-tenant.us.auth0.com"
AUTH0_AUDIENCE = "https://api.tilli.com/chatbot"
CLIENT_ID = "YOUR_CLIENT_ID"  # Get from Auth0 Dashboard → Applications → Test Application
CLIENT_SECRET = "YOUR_CLIENT_SECRET"  # Same place

# Get token
response = requests.post(
    f"https://{AUTH0_DOMAIN}/oauth/token",
    json={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "audience": AUTH0_AUDIENCE,
        "grant_type": "client_credentials"
    }
)

token = response.json().get("access_token")
print(f"Access Token:\n{token}")
```

### 5.2: Test with `client.py`

Update your `client.py` to use the Auth0 token:

```python
# Replace the mock token with your Auth0 token
headers = {
    "Authorization": f"Bearer {AUTH0_TOKEN_HERE}",
    "Content-Type": "application/json"
}

response = requests.post(
    "http://localhost:8000/agent/ask",
    headers=headers,
    json={"question": "How did School 1 perform?"}
)

print(response.json())
```

### 5.3: Verify Access Control

Test that school isolation works:

1. **Valid Access** (should work):
   - User with `school_id: "School 1"`
   - Asks: "How did School 1 perform?"
   - ✅ Should return data

2. **Invalid Access** (should be blocked):
   - User with `school_id: "School 1"`
   - Asks: "How did School 2 perform?"
   - ❌ Should return `403 Forbidden`

---

## Troubleshooting

### Issue: "Invalid token signature"

**Cause**: The token might be expired or the `AUTH0_DOMAIN` is incorrect.

**Solution**:
- Verify `AUTH0_DOMAIN` in `.env` matches your Auth0 tenant
- Get a fresh token (tokens expire after 24 hours by default)

### Issue: "Incorrect claims (check audience/issuer)"

**Cause**: The `AUTH0_AUDIENCE` doesn't match.

**Solution**:
- Verify `AUTH0_AUDIENCE` in `.env` matches the API Identifier in Auth0
- When requesting a token, ensure you specify the correct `audience`

### Issue: "Missing role or school_id in token"

**Cause**: The Action isn't running or user metadata isn't set.

**Solution**:
- Verify the Action is deployed and added to the Login flow
- Check user's `app_metadata` has `role` and `school_id`
- Decode your token at [jwt.io](https://jwt.io) to inspect claims

### Issue: Server still using local dev mode

**Cause**: Environment variables not loaded.

**Solution**:
- Ensure `.env` file is in the project root
- Restart the server completely
- Check server logs for "Auth0" mentions

---

## Production Considerations

### 1. **User Provisioning**

In production, you'll want to:
- Sync users from your existing database
- Use Auth0's Management API to create users programmatically
- Or integrate with Clever/ClassLink for school SSO

### 2. **Role Assignment**

Set up a process to assign roles and school IDs:
- During user registration
- Via Auth0 Management API
- Through a custom admin dashboard

### 3. **Token Expiration**

Configure token lifetimes in Auth0:
- Go to **Applications → APIs → Settings**
- Adjust **Token Expiration** (default: 86400 seconds = 24 hours)

### 4. **Security**

- **Never commit** `CLIENT_SECRET` to Git
- Use environment variables or secret managers (Azure Key Vault, AWS Secrets Manager, GCP Secret Manager)
- Enable MFA for admin accounts in Auth0

### 5. **Multi-Factor Authentication (MFA)** 🔒 **RECOMMENDED**

**Why MFA is Critical for Tilli:**
- Protects FERPA-regulated student data
- Required for UNICEF compliance audits
- Industry standard for EdTech platforms
- Prevents unauthorized access even if passwords are compromised

**When to Enable MFA:**
- ✅ **Always** for admin accounts
- ✅ **Recommended** for all educator accounts in production
- ⚠️ **Optional** for read-only users (depending on data sensitivity)

**How to Enable MFA in Auth0:**

1. **Navigate to MFA Settings**:
   - Go to **Security → Multi-factor Auth** in Auth0 Dashboard

2. **Choose MFA Methods**:
   - **TOTP (Recommended)**: Google Authenticator, Authy, etc. (Free)
   - **SMS**: Text message codes (May incur costs)
   - **Push Notifications**: Auth0 Guardian app (Free)
   - **Email**: Email-based codes (Free)

3. **Configure MFA Policy**:
   - **Always**: Require MFA for all users
   - **Adaptive**: Require MFA based on risk (location, device, etc.)
   - **Never**: MFA disabled (not recommended for production)

4. **Recommended Configuration**:
   ```
   MFA Policy: Always (for production)
   Allowed Methods: TOTP + Push Notifications
   Enrollment: Required on first login
   ```

5. **Test MFA**:
   - Log in as a test user
   - You'll be prompted to set up MFA
   - Scan QR code with authenticator app
   - Verify it works

**No Code Changes Needed!**
- Auth0 handles the entire MFA flow
- Your API receives verified tokens as usual
- Users see MFA prompts automatically

**Cost**: 
- TOTP/Push: Included in free tier (up to 7,000 MAU)
- SMS: May incur per-message costs

**Documentation**: [Auth0 MFA Guide](https://auth0.com/docs/secure/multi-factor-authentication)

---

## Additional Resources

- [Auth0 Documentation](https://auth0.com/docs)
- [Auth0 Actions](https://auth0.com/docs/customize/actions)
- [JWT Debugger](https://jwt.io)
- [Auth0 Management API](https://auth0.com/docs/api/management/v2)

---

## Need Help?

If you encounter issues:
1. Check the server logs for detailed error messages
2. Decode your token at jwt.io to verify claims
3. Review Auth0 Dashboard → Monitoring → Logs for authentication events
