"""Sign in with Google (OAuth 2.0 authorization code flow with PKCE and OpenID Connect).

The browser is sent to Google with a random `state` (CSRF) and a PKCE challenge; Google sends
it back to /api/auth/google/callback with a code, which the server exchanges for tokens over TLS
and uses to read the verified profile from Google's userinfo endpoint.
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105  # a URL, not a password
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class GoogleAuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class GoogleProfile:
    sub: str
    email: str
    email_verified: bool
    name: str | None


def new_state() -> str:
    return secrets.token_urlsafe(32)


def new_code_verifier() -> str:
    return secrets.token_urlsafe(64)  # 86 characters, within PKCE's 43-128


def code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


class GoogleOAuth:
    def __init__(self, *, client_id: str, client_secret: str, redirect_uri: str, http: httpx.Client | None = None):
        self.client_id = client_id
        self._client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._http = http or httpx.Client(timeout=10)

    def authorization_url(self, *, state: str, code_verifier: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": code_challenge(code_verifier),
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    def fetch_profile(self, *, code: str, code_verifier: str) -> GoogleProfile:
        try:
            token = self._http.post(
                TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                    "code_verifier": code_verifier,
                },
            )
            token.raise_for_status()
            access_token = token.json()["access_token"]
            info = self._http.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
            info.raise_for_status()
            data = info.json()
            return GoogleProfile(
                sub=str(data["sub"]),
                email=str(data["email"]),
                email_verified=bool(data.get("email_verified")),
                name=data.get("name"),
            )
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise GoogleAuthError(f"Google sign-in failed: {type(exc).__name__}") from exc
