#!/usr/bin/env python3
"""Daily check that the App Review demo account can actually get into both apps.

Added 04/11/2026 after Google rejected Live Desk twice (23/10, 27/10) for a failed
reviewer sign-in: the account had never been confirmed and had no access row, and
nothing looked. Exit 0 = fit for review, 1 = fault (the workflow goes red and the
GitHub failure triage picks it up), 2 = could not check. It prints no secrets.

Env: SUPABASE_URL, SUPABASE_SERVICE_KEY. Optional SUPABASE_ANON_KEY plus
LIVEDESK_REVIEWER_PASSWORD (a repo secret only Lou sets) add a real password sign-in.
"""
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

EMAIL = "review@elevateandthrive.uk"
MIN_ACCESS_DAYS = 14


def faults_for(user, access, member, now):
    """The reasons a reviewer could not get in. Empty list = fit for review."""
    if not user:
        return ["account does not exist"]
    out = []
    if not user.get("email_confirmed_at"):
        out.append("email not confirmed: password sign-in fails whatever the password")
    banned = parse(user.get("banned_until"))
    if banned and banned > now:
        out.append("account is banned")
    until = parse((access or {}).get("store_expires_at"))
    if not until:
        out.append("no Live Desk access: reviewer would land on the paywall")
    elif until < now + dt.timedelta(days=MIN_ACCESS_DAYS):
        out.append(f"Live Desk access ends {until.date()}, under {MIN_ACCESS_DAYS} days away")
    if (member or {}).get("status") != "approved":
        out.append("no approved Industry Nurses membership")
    return out


def parse(value):
    if not value:
        return None
    return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def call(url, headers, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers={**headers, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, None


def main():
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not base or not key:
        print("NOT CHECKED: SUPABASE_URL or SUPABASE_SERVICE_KEY missing")
        return 2
    h = {"apikey": key, "Authorization": "Bearer " + key}
    try:
        code, page = call(f"{base}/auth/v1/admin/users?per_page=1000", h)
        if code != 200:
            print(f"NOT CHECKED: admin users returned {code}")
            return 2
        user = next((u for u in page.get("users", []) if (u.get("email") or "").lower() == EMAIL), None)
        access = member = None
        if user:
            q = urllib.parse.quote(user["id"])
            _, rows = call(f"{base}/rest/v1/livedesk_access?select=store_expires_at&user_id=eq.{q}", h)
            access = rows[0] if rows else None
            _, rows = call(f"{base}/rest/v1/ain_members?select=status&id=eq.{q}", h)
            member = rows[0] if rows else None
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"NOT CHECKED: {type(e).__name__}")
        return 2

    faults = faults_for(user, access, member, dt.datetime.now(dt.timezone.utc))
    anon, pw = os.environ.get("SUPABASE_ANON_KEY", ""), os.environ.get("LIVEDESK_REVIEWER_PASSWORD", "")
    if anon and pw:
        code, res = call(f"{base}/auth/v1/token?grant_type=password", {"apikey": anon}, {"email": EMAIL, "password": pw})
        if code != 200:
            faults.append(f"real password sign-in failed: {(res or {}).get('error_code', code)}")
        else:
            print("real password sign-in: ok")
    else:
        print("real password sign-in: not checked (secret not set)")

    for f in faults:
        print("FAULT:", f)
    if faults:
        return 1
    print("Reviewer account fit for review")
    return 0


if __name__ == "__main__":
    sys.exit(main())
