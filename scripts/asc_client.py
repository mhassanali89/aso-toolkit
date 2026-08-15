#!/usr/bin/env python3
"""
Shared App Store Connect API client: JWT auth (ES256) + a thin requests wrapper
with pagination. Used by pull_asc_analytics.py and push_aso_metadata.py.

Setup:
    pip install pyjwt cryptography requests
    export ASC_ISSUER_ID=...      # App Store Connect → Users and Access → Integrations
    export ASC_KEY_ID=...         # the key's ID
    export ASC_APP_ID=...         # your app's Apple ID (numeric)
    export ASC_PRIVATE_KEY_PATH=/path/to/AuthKey_<KEY_ID>.p8

IMPORTANT: the API key must have the Admin role. Narrower roles (Developer,
Marketing, "Sales and Reports", etc.) can list apps but will get 403s on
anything that writes metadata or requests analytics/sales reports.

Never commit the .p8 file. Keep it outside the repo or in a gitignored path.
"""

import os
import sys
import time
from pathlib import Path

import jwt
import requests

BASE_URL = "https://api.appstoreconnect.apple.com/v1"
JWT_TTL_SECONDS = 19 * 60  # Apple caps this at 20 minutes; stay under it


def _env(name: str, default: str = None) -> str:
    val = os.environ.get(name, default)
    if val is None:
        sys.exit(f"Missing required environment variable: {name}")
    return val


class Client:
    """Authenticated App Store Connect API client.

    Reads config from environment variables (see module docstring) at
    construction time, so you can `Client()` with no arguments once the env
    vars are set.
    """

    def __init__(self):
        self.issuer_id = _env("ASC_ISSUER_ID")
        self.key_id = _env("ASC_KEY_ID")
        self.app_id = os.environ.get("ASC_APP_ID")  # not required by every caller
        key_path = os.environ.get(
            "ASC_PRIVATE_KEY_PATH", str(Path.cwd() / f"AuthKey_{self.key_id}.p8")
        )
        p = Path(key_path)
        if not p.exists():
            sys.exit(
                f"Private key not found at {p}\n"
                f"Set ASC_PRIVATE_KEY_PATH or place AuthKey_{self.key_id}.p8 in the cwd."
            )
        self._private_key = p.read_text()

        self._token = None
        self._token_issued_at = 0
        self.session = requests.Session()

    def _make_token(self) -> str:
        now = int(time.time())
        payload = {
            "iss": self.issuer_id,
            "iat": now,
            "exp": now + JWT_TTL_SECONDS,
            "aud": "appstoreconnect-v1",
        }
        headers = {"alg": "ES256", "kid": self.key_id, "typ": "JWT"}
        return jwt.encode(payload, self._private_key, algorithm="ES256", headers=headers)

    def _headers(self):
        if self._token is None or time.time() - self._token_issued_at > JWT_TTL_SECONDS - 60:
            self._token = self._make_token()
            self._token_issued_at = time.time()
        return {"Authorization": f"Bearer {self._token}"}

    def get(self, url, **kwargs):
        if not url.startswith("http"):
            url = f"{BASE_URL}{url}"
        r = self.session.get(url, headers=self._headers(), **kwargs)
        if r.status_code >= 400:
            sys.exit(f"GET {url} -> {r.status_code}\n{r.text}")
        return r.json()

    def post(self, url, json_body, **kwargs):
        if not url.startswith("http"):
            url = f"{BASE_URL}{url}"
        r = self.session.post(url, headers=self._headers(), json=json_body, **kwargs)
        if r.status_code >= 400:
            sys.exit(f"POST {url} -> {r.status_code}\n{r.text}")
        return r.json()

    def patch(self, url, resource_type, resource_id, attributes):
        """PATCH a single resource's attributes. Returns (ok, response_json_or_text)."""
        if not url.startswith("http"):
            url = f"{BASE_URL}{url}"
        body = {"data": {"type": resource_type, "id": resource_id, "attributes": attributes}}
        r = self.session.patch(url, headers=self._headers(), json=body)
        if r.status_code == 200:
            return True, r.json()
        return False, r.text

    def paginate(self, url, params=None):
        """Yield all `data` items across pages, following `links.next`."""
        next_url, next_params = url, params
        while next_url:
            body = self.get(next_url, params=next_params)
            for item in body.get("data", []):
                yield item
            next_url = body.get("links", {}).get("next")
            next_params = None  # params are baked into `next` already
