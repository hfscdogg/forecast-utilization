"""
Thin Zoho CRM REST client for inspection work.

Local-only. Production Deluge code does not use this — it runs inside Creator
with its own auth context. This exists so the math can be validated against
real CRM data from this sandbox before the Deluge port is written.
"""

import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent / ".env"


def load_env() -> dict[str, str]:
    env = {}
    if not ENV_PATH.exists():
        raise RuntimeError(f"Missing {ENV_PATH}; copy .env.example and fill in.")
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


_token_cache: dict[str, object] = {"access_token": None, "expires_at": 0.0}


def get_access_token() -> str:
    """Exchange refresh token for an access token. Cache for 50 minutes."""
    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["access_token"]  # type: ignore[return-value]

    env = load_env()
    url = f"https://{env['ZOHO_ACCOUNTS_DOMAIN']}/oauth/v2/token"
    data = urllib.parse.urlencode(
        {
            "refresh_token": env["ZOHO_REFRESH_TOKEN"],
            "client_id": env["ZOHO_CLIENT_ID"],
            "client_secret": env["ZOHO_CLIENT_SECRET"],
            "grant_type": "refresh_token",
        }
    ).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())
    if "access_token" not in body:
        raise RuntimeError(f"Token exchange failed: {body}")
    _token_cache["access_token"] = body["access_token"]
    _token_cache["expires_at"] = time.time() + 50 * 60
    return body["access_token"]


def api_get(path: str, params: dict | None = None) -> dict:
    env = load_env()
    base = f"https://{env['ZOHO_API_DOMAIN']}"
    url = base + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    token = get_access_token()
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Zoho-oauthtoken {token}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def api_post(path: str, body: dict) -> dict:
    env = load_env()
    base = f"https://{env['ZOHO_API_DOMAIN']}"
    url = base + path
    token = get_access_token()
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Zoho-oauthtoken {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def coql(query: str) -> dict:
    """Run a COQL query against Zoho CRM v6."""
    return api_post("/crm/v6/coql", {"select_query": query})


if __name__ == "__main__":
    org = api_get("/crm/v6/org")
    print(json.dumps(org, indent=2))
