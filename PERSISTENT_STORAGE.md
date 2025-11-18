# 💾 Persistent Storage Setup (GitHub Gist)

Since Koyeb free tier has ephemeral storage, user preferences are lost after redeploy. This guide shows how to use GitHub Gist for free persistent storage.

---

## 🎯 What Gets Saved

- ✅ User queue selections
- ✅ Notification preferences
- ✅ Last update timestamp

---

## 📝 Setup Steps

### 1. **Create a GitHub Personal Access Token**

1. Go to https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Set:
   - **Note**: `Yasno Bot Storage`
   - **Expiration**: No expiration (or 1 year)
   - **Scopes**: Check only `gist` (create gists)
4. Click **"Generate token"**
5. **Copy the token** (you won't see it again!)

### 2. **Create a GitHub Gist**

1. Go to https://gist.github.com
2. Click **"+ New gist"**
3. Set:
   - **Filename**: `user_preferences.json`
   - **Content**: `{}`
   - **Visibility**: **Secret** (recommended)
4. Click **"Create secret gist"**
5. **Copy the Gist ID** from URL:
   ```
   https://gist.github.com/USERNAME/abc123def456  
                                   ↑ This is your GIST_ID
   ```

### 3. **Add Environment Variables to Koyeb**

1. Go to [app.koyeb.com](https://app.koyeb.com)
2. Click on your `yasno-bot` service
3. Click **"Settings"** → **"Environment variables"**
4. Add two new variables:
   ```
   GITHUB_TOKEN=ghp_your_token_here
   GIST_ID=abc123def456
   ```
5. Click **"Save"** → Service will auto-redeploy

---

## ✅ Verification

After redeploy, check logs:
```
INFO - Loading preferences from GitHub Gist...
INFO - Loaded preferences from Gist for X users
```

---

## 🔄 How It Works

- **On startup**: Bot loads preferences from Gist → saves to local file as backup
- **On changes**: Bot saves to both local file AND Gist
- **On redeploy**: Bot loads from Gist (local file is lost but Gist persists)

---

## 🆓 Why GitHub Gist?

- ✅ **100% FREE** forever
- ✅ No credit card required
- ✅ Simple API
- ✅ Already have GitHub account
- ✅ Version history (can restore old data)
- ✅ Works perfectly with Koyeb

---

## 🔒 Security

- Use **secret gist** (not public)
- Token only has `gist` scope (minimal permissions)
- Can revoke token anytime at https://github.com/settings/tokens

---

## 🆘 Troubleshooting

### Bot logs show "Failed to load from GitHub Gist"
- Check `GITHUB_TOKEN` is correct
- Check `GIST_ID` is correct
- Verify token has `gist` scope
- Check token hasn't expired

### Preferences still lost after redeploy
- Verify both env vars are set in Koyeb
- Check logs for Gist loading messages
- Make sure service redeployed after adding env vars

---

## 🎉 Done!

Your bot will now remember all user preferences across redeploys! 🚀
