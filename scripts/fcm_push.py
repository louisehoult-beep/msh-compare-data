"""fcm_push.py — native phone alerts for the Live Desk app, via Firebase Cloud
Messaging (HTTP v1). Added 01/10/2026 with the Live Desk app (livedesk-app/).

push_alerts.py `send` builds ONE digest per subscriber per slot (9am, 12 noon,
4pm London) for the web alerts app. The Live Desk app gets the same digest,
from the same new-items diff, through this module: FCM delivers to Android
directly and to iPhone through Apple's APNs (the APNs key is uploaded to the
Firebase project once, by hand).

Targets come from the Supabase view livedesk_push_targets, which returns only
devices whose app account has current access (Hub member link or store
subscription). The view is the access rule; members_only() in push_alerts.py
is the same idea for web push.

Secret: FCM_SERVICE_ACCOUNT (the Firebase service account JSON, whole file).
Missing -> push_alerts.py skips app delivery and says so. cryptography is
imported lazily (pywebpush already installs it in push-alerts.yml).
"""
from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request

TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
VIEW = "livedesk_push_targets"
DEVICES = "livedesk_devices"
DATA_MAX = 3000   # FCM data payload limit is 4 KB; stay well under


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def signed_jwt(sa: dict, now: int | None = None) -> str:
    """RS256 assertion for the OAuth token exchange (RFC 7523)."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    now = int(now or time.time())
    head = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claims = _b64url(json.dumps({"iss": sa["client_email"], "scope": SCOPE, "aud": TOKEN_URL,
                                 "iat": now, "exp": now + 3600}).encode())
    key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
    sig = key.sign((head + "." + claims).encode(), padding.PKCS1v15(), hashes.SHA256())
    return head + "." + claims + "." + _b64url(sig)


def access_token(sa: dict, opener=urllib.request.urlopen) -> str:
    body = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                                   "assertion": signed_jwt(sa)}).encode()
    with opener(urllib.request.Request(TOKEN_URL, data=body, method="POST"), timeout=30) as r:
        return json.loads(r.read())["access_token"]


def to_fcm(token: str, msg: dict) -> dict:
    """The digest push_alerts.build_message made -> one FCM v1 message.

    Notification text shows with the app closed; data carries the items so
    the app's Alerts tab can list them without another fetch. FCM data
    values must be strings."""
    items = list(msg.get("items") or [])
    data = {"kind": "digest", "tag": msg.get("tag", ""), "more": str(msg.get("more", 0))}
    while True:
        data["items"] = json.dumps(items, ensure_ascii=False)
        if not items or len(json.dumps(data, ensure_ascii=False).encode("utf-8")) <= DATA_MAX:
            break
        items.pop()
    return {"message": {
        "token": token,
        "notification": {"title": msg["title"], "body": msg["body"]},
        "data": data,
        "android": {"priority": "high", "notification": {"tag": msg.get("tag", "")}},
        "apns": {"headers": {"apns-priority": "10", "apns-collapse-id": msg.get("tag", "")[:64]},
                 "payload": {"aps": {"sound": "default"}}},
    }}


def sender(sa: dict, opener=urllib.request.urlopen):
    """send(row, message) -> (ok, gone, detail), the shape push_alerts.deliver takes."""
    bearer = access_token(sa, opener)
    url = "https://fcm.googleapis.com/v1/projects/%s/messages:send" % sa["project_id"]

    def send(row: dict, message: dict):
        req = urllib.request.Request(url, data=json.dumps(to_fcm(row["token"], message)).encode(),
                                     method="POST")
        req.add_header("Authorization", "Bearer " + bearer)
        req.add_header("Content-Type", "application/json")
        try:
            with opener(req, timeout=30):
                return True, False, "sent"
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:200]
            # UNREGISTERED (404) or an invalid token (400 INVALID_ARGUMENT
            # naming the token): the app was removed or the token rotated.
            gone = exc.code == 404 or (exc.code == 400 and "registration token" in detail.lower())
            return False, gone, "HTTP %s: %s" % (exc.code, detail)
        except Exception as exc:   # network etc. — report, do not prune
            return False, False, "error: %s" % str(exc)[:200]
    return send


def targets(store) -> list[dict]:
    """Devices with current access, as deliver() rows. store: push_alerts.Store."""
    base = store.base
    store.base = base[: base.rindex("/") + 1] + VIEW
    try:
        rows = store._req("GET", "?select=token,platform,specialities&limit=5000") or []
    finally:
        store.base = base
    return [dict(r, endpoint="https://fcm.googleapis.com/" + (r.get("platform") or "app"))
            for r in rows if r.get("token")]


def forget(store, token: str) -> None:
    base = store.base
    store.base = base[: base.rindex("/") + 1] + DEVICES
    try:
        store._req("DELETE", "?token=eq.%s" % urllib.parse.quote(token, safe=""),
                   prefer="return=minimal")
    finally:
        store.base = base
