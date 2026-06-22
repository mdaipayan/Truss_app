# Visitor Tracking — Setup Guide

The app records **one anonymous row per browser session** (a UTC timestamp and a
random session ID) to a Google Sheet. No IP addresses or personal data are
stored. Visit stats are visible only to you, through the password-protected
**🔐 Admin** panel in the app's left sidebar.

If you skip this setup the app still runs perfectly — visitor logging simply
stays switched off.

---

## What you need
- A Google account
- A free Google Cloud project (for a *service account*)
- One Google Sheet that will hold the log

## Step 1 — Create the Google Sheet
1. Create a new blank Google Sheet (e.g. name it `Truss Visitor Log`).
2. Copy its **key** from the URL — the long string between `/d/` and `/edit`:
   `https://docs.google.com/spreadsheets/d/`**`THIS_IS_THE_KEY`**`/edit`

## Step 2 — Create a service account
1. Go to https://console.cloud.google.com/ and create (or pick) a project.
2. Enable the **Google Sheets API**: APIs & Services → Library → search
   "Google Sheets API" → Enable.
3. APIs & Services → Credentials → **Create credentials → Service account**.
   Give it a name like `truss-logger`, then Create.
4. Open the new service account → **Keys → Add key → Create new key → JSON**.
   A `.json` file downloads — keep it private.

## Step 3 — Share the Sheet with the service account
1. Open the downloaded JSON and copy the `client_email` value
   (looks like `truss-logger@your-project.iam.gserviceaccount.com`).
2. In your Google Sheet, click **Share** and give that email **Editor** access.
   (This is what lets the app write to the sheet.)

## Step 4 — Add the secrets
Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill it
in using the JSON file from Step 2:
- `admin_password` — whatever password you want to type into the Admin panel.
- `[gcp_service_account]` — copy each field from the JSON. For `private_key`,
  keep the `\n` sequences exactly as they appear in the JSON.
- `[visitor_log] sheet_key` — the key from Step 1.

**Never commit `secrets.toml`** — it's already listed in `.gitignore`.

### On Streamlit Community Cloud
Don't upload the file. Instead open your app → **Settings → Secrets** and paste
the same TOML contents there. Then reboot the app.

## Step 5 — Install the new dependencies
```bash
pip install -r requirements.txt
```
(adds `gspread` and `google-auth`)

## Step 6 — Use it
1. Run the app. New visits start appearing as rows in your Google Sheet.
2. Open the sidebar **🔐 Admin** panel, enter your `admin_password`, and you'll
   see total visits, unique sessions, the full log, and a CSV download.

---

## Notes
- "Per session" means one row per browser tab/session, not per page rerun.
- If the Sheet/credentials are ever unreachable, logging silently skips so
  visitors are never affected.

---

# Part B — Verified identity via Google sign-in (optional)

With this enabled, visitors must sign in with Google before using the app, and
each logged visit includes their **verified name and email**. If you do NOT add
the `[auth]` block, the app simply runs without a login wall (anonymous logging).

> Note: this uses a Google **OAuth Client ID**, which is a *different* credential
> from the service account in Part A.

## Step 1 — Create an OAuth Client ID
1. Google Cloud Console → APIs & Services → **OAuth consent screen**. Configure
   it (User type "External" is fine), add yourself as a test user, and save.
2. APIs & Services → **Credentials → Create credentials → OAuth client ID**.
3. Application type: **Web application**.
4. Under **Authorized redirect URIs**, add the URLs your app runs at, each ending
   in `/oauth2callback`:
   - Local: `http://localhost:8501/oauth2callback`
   - Cloud: `https://YOUR-APP.streamlit.app/oauth2callback`
5. Create, then copy the **Client ID** and **Client secret**.

## Step 2 — Fill in the [auth] secrets
In `.streamlit/secrets.toml` (and/or the Streamlit Cloud Secrets box), complete
the `[auth]` block:
- `client_id` / `client_secret` — from Step 1.
- `redirect_uri` — must exactly match one you registered (use the localhost one
  for local runs, the streamlit.app one when deployed).
- `cookie_secret` — a long random string (already generated in your local file;
  regenerate with `python -c "import secrets; print(secrets.token_hex(32))"`).

## Step 3 — Install deps and run
```bash
pip install -r requirements.txt   # adds Authlib, bumps Streamlit to >= 1.42
streamlit run app.py
```
You'll see a "Sign in with Google" screen. After signing in, your visit (name +
email) is recorded, and a "Log out" button appears in the sidebar.

## Notes on sign-in
- Requires Streamlit >= 1.42.
- While the OAuth consent screen is in "Testing" mode, only the test users you
  added can sign in. To open it to everyone, publish the consent screen
  (may require Google verification depending on scopes; basic name/email is light).
- The login wall reduces casual usage — anyone who won't sign in can't use the
  tool. To make login optional instead, tell the developer and it's a small change
  (remove the `st.stop()` gate, keep a "Sign in" button).
