"""Generic OIDC single sign-on (authorization-code flow).

Works with any standards-compliant identity provider (Keycloak, Azure AD,
Okta, gov IdPs): configure the discovery URL + client credentials. Users are
JIT-provisioned into the configured SSO tenant on first login.

The CSRF `state` parameter is a self-contained HMAC-signed token
(timestamp.nonce.signature) so no server-side session storage is needed —
`make_state`/`verify_state` are pure and unit-testable.
"""

import hashlib
import hmac
import secrets
import time

import httpx

from app.core.config import get_settings

_discovery_cache: dict[str, dict] = {}


class SSONotConfigured(Exception):
    pass


def _require_config() -> None:
    s = get_settings()
    if not (s.oidc_discovery_url and s.oidc_client_id and s.oidc_client_secret and s.oidc_redirect_uri):
        raise SSONotConfigured(
            "SSO is not configured: set LEGALOS_OIDC_DISCOVERY_URL, LEGALOS_OIDC_CLIENT_ID, "
            "LEGALOS_OIDC_CLIENT_SECRET and LEGALOS_OIDC_REDIRECT_URI"
        )


# --- CSRF state ---

def _sign(payload: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]


def make_state(secret: str | None = None, now: float | None = None) -> str:
    secret = secret or get_settings().secret_key
    payload = f"{int(now or time.time())}.{secrets.token_urlsafe(16)}"
    return f"{payload}.{_sign(payload, secret)}"


def verify_state(state: str, secret: str | None = None, now: float | None = None) -> bool:
    settings = get_settings()
    secret = secret or settings.secret_key
    parts = state.split(".")
    if len(parts) != 3:
        return False
    timestamp, nonce, signature = parts
    payload = f"{timestamp}.{nonce}"
    if not hmac.compare_digest(_sign(payload, secret), signature):
        return False
    try:
        issued_at = int(timestamp)
    except ValueError:
        return False
    return (now or time.time()) - issued_at <= settings.sso_state_ttl_seconds


# --- OIDC protocol ---

async def _discovery() -> dict:
    s = get_settings()
    if s.oidc_discovery_url not in _discovery_cache:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(s.oidc_discovery_url)
            resp.raise_for_status()
            _discovery_cache[s.oidc_discovery_url] = resp.json()
    return _discovery_cache[s.oidc_discovery_url]


async def build_authorization_url() -> tuple[str, str]:
    """Returns (authorization_url, state)."""
    _require_config()
    s = get_settings()
    doc = await _discovery()
    state = make_state()
    params = httpx.QueryParams(
        {
            "response_type": "code",
            "client_id": s.oidc_client_id,
            "redirect_uri": s.oidc_redirect_uri,
            "scope": "openid email profile",
            "state": state,
        }
    )
    return f"{doc['authorization_endpoint']}?{params}", state


async def exchange_code(code: str) -> dict:
    """Exchange the authorization code and return userinfo claims."""
    _require_config()
    s = get_settings()
    doc = await _discovery()
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_resp = await client.post(
            doc["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": s.oidc_redirect_uri,
                "client_id": s.oidc_client_id,
                "client_secret": s.oidc_client_secret,
            },
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        userinfo_resp = await client.get(
            doc["userinfo_endpoint"], headers={"Authorization": f"Bearer {access_token}"}
        )
        userinfo_resp.raise_for_status()
        return userinfo_resp.json()
