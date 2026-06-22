"""Privacy-respecting visitor logging for the Truss Suite.

Records one row per browser session (UTC timestamp + an anonymous, random
session id) to a Google Sheet so the record survives Streamlit Community Cloud
redeploys. No IP addresses or personal data are stored.

Everything here is defensive: if the Google credentials/secrets are not set up,
all functions become safe no-ops and the app keeps working normally.

Required Streamlit secrets (see secrets.toml.example):

    admin_password = "choose-a-password"

    [gcp_service_account]
    type = "service_account"
    ...full service-account JSON fields...

    [visitor_log]
    # provide ONE of these (key is the part of the sheet URL after /d/):
    sheet_key = "1AbC...."
    # sheet_url = "https://docs.google.com/spreadsheets/d/.../edit"
"""

import datetime
import uuid

import streamlit as st

SHEET_HEADER = ["timestamp_utc", "session_id", "event"]
_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _secret_has(key):
    try:
        return key in st.secrets
    except Exception:
        return False


def _secret_get(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return default


@st.cache_resource(show_spinner=False)
def _get_worksheet():
    """Return the gspread worksheet, or None if logging is not configured.

    Cached as a resource so we authorize once per server process, not per run.
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        return None

    if not _secret_has("gcp_service_account"):
        return None

    try:
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=_SCOPES
        )
        client = gspread.authorize(creds)

        cfg = _secret_get("visitor_log", {}) or {}
        try:
            sheet_key = cfg.get("sheet_key")
            sheet_url = cfg.get("sheet_url")
        except AttributeError:
            sheet_key, sheet_url = None, None

        if sheet_key:
            spreadsheet = client.open_by_key(sheet_key)
        elif sheet_url:
            spreadsheet = client.open_by_url(sheet_url)
        else:
            return None

        worksheet = spreadsheet.sheet1

        # Ensure a header row exists exactly once.
        try:
            if not worksheet.get_all_values():
                worksheet.append_row(SHEET_HEADER, value_input_option="USER_ENTERED")
        except Exception:
            pass

        return worksheet
    except Exception:
        return None


def is_configured():
    """True if visitor logging is wired up and reachable."""
    return _get_worksheet() is not None


def log_visit():
    """Record a single visit for this browser session (idempotent per session).

    Safe no-op when logging is not configured or the network call fails.
    """
    if st.session_state.get("_visit_logged"):
        return

    # Mark first so a failed network call doesn't retry every rerun this session.
    st.session_state["_visit_logged"] = True

    session_id = st.session_state.get("_session_id")
    if not session_id:
        session_id = uuid.uuid4().hex[:12]
        st.session_state["_session_id"] = session_id

    worksheet = _get_worksheet()
    if worksheet is None:
        return

    try:
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
        worksheet.append_row(
            [timestamp, session_id, "visit"], value_input_option="USER_ENTERED"
        )
    except Exception:
        # Logging must never break the app for a visitor.
        pass


def get_visit_records():
    """Return a list of dict rows from the sheet, or None if unavailable."""
    worksheet = _get_worksheet()
    if worksheet is None:
        return None
    try:
        return worksheet.get_all_records()
    except Exception:
        return None
