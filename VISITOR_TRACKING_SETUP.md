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
- Your own visits are counted too — there's no way to perfectly distinguish you
  from others without a login. You can identify your sessions by the times you
  opened the app, or filter them out in the downloaded CSV.
- If the Sheet/credentials are ever unreachable, logging silently skips so
  visitors are never affected.
