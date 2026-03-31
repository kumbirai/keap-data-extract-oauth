"""HTTP client for Revolut Business API with token lifecycle and retries."""
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from src.revolut.api_constants import (
    ACCOUNTS_PATH,
    CLIENT_ASSERTION_TYPE,
    DEFAULT_BACKOFF_INITIAL_SECONDS,
    DEFAULT_BACKOFF_MAX_SECONDS,
    DEFAULT_MAX_HTTP_ATTEMPTS,
    TOKEN_EXPIRY_SKEW_SECONDS,
    TRANSACTIONS_PATH,
)
from src.revolut.auth import build_client_assertion_jwt, load_signing_key
from src.revolut.settings import RevolutExtractSettings

logger = logging.getLogger(__name__)


class RevolutApiError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class RevolutClient:
    def __init__(self, settings: RevolutExtractSettings):
        self._settings = settings
        self._private_key = load_signing_key(settings)
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def _exchange_token(self) -> Tuple[str, int]:
        assertion = build_client_assertion_jwt(self._settings, self._private_key)
        data: Dict[str, str] = {
            "client_id": self._settings.client_id,
            "client_assertion_type": CLIENT_ASSERTION_TYPE,
            "client_assertion": assertion,
        }
        if self._settings.refresh_token:
            data["grant_type"] = "refresh_token"
            data["refresh_token"] = self._settings.refresh_token
        elif self._settings.authorization_code:
            data["grant_type"] = "authorization_code"
            data["code"] = self._settings.authorization_code
        else:
            raise RevolutApiError("No refresh token or authorization code configured")

        resp = requests.post(
            self._settings.token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=60,
        )
        if resp.status_code >= 400:
            logger.error(
                "Revolut token exchange failed: status=%s body=%s",
                resp.status_code,
                (resp.text or "")[:500],
            )
            raise RevolutApiError(
                f"Token exchange failed: HTTP {resp.status_code}",
                status_code=resp.status_code,
                body=resp.text,
            )
        payload = resp.json()
        access = payload.get("access_token")
        if not access or not isinstance(access, str):
            raise RevolutApiError("Token response missing access_token")
        expires_in = int(payload.get("expires_in") or 2400)
        return access, expires_in

    def _ensure_token(self) -> str:
        now = time.time()
        if self._access_token and now < self._token_expires_at - TOKEN_EXPIRY_SKEW_SECONDS:
            return self._access_token
        token, expires_in = self._exchange_token()
        self._access_token = token
        self._token_expires_at = now + float(expires_in)
        return token

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = f"{self._settings.api_base_url}{path}"
        token = self._ensure_token()
        headers = {"Authorization": f"Bearer {token}"}

        def call():
            r = requests.request(method, url, params=params, headers=headers, timeout=120)
            return r

        delay = DEFAULT_BACKOFF_INITIAL_SECONDS
        last_exc: Optional[Exception] = None
        for attempt in range(DEFAULT_MAX_HTTP_ATTEMPTS):
            resp = call()
            if resp.status_code == 429 or resp.status_code >= 500:
                last_exc = RevolutApiError(
                    f"HTTP {resp.status_code}",
                    status_code=resp.status_code,
                    body=resp.text,
                )
                logger.warning(
                    "Revolut HTTP %s, sleeping %.1fs (attempt %s) path=%s",
                    resp.status_code,
                    delay,
                    attempt + 1,
                    path,
                )
                time.sleep(delay)
                delay = min(delay * 2, DEFAULT_BACKOFF_MAX_SECONDS)
                token = self._ensure_token()
                headers["Authorization"] = f"Bearer {token}"
                continue
            if resp.status_code >= 400:
                logger.error(
                    "Revolut API error: status=%s path=%s body=%s",
                    resp.status_code,
                    path,
                    (resp.text or "")[:800],
                )
                raise RevolutApiError(
                    f"API request failed: HTTP {resp.status_code}",
                    status_code=resp.status_code,
                    body=resp.text,
                )
            if not resp.content:
                return None
            return resp.json()
        if last_exc:
            raise last_exc
        raise RevolutApiError("Revolut backoff exhausted")

    def list_accounts(self) -> List[Dict[str, Any]]:
        data = self._request_json("GET", ACCOUNTS_PATH)
        if data is None:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("accounts", "data", "results"):
                inner = data.get(key)
                if isinstance(inner, list):
                    return inner
        raise RevolutApiError("Unexpected accounts response shape")

    def list_transactions(
        self,
        *,
        account_id: str,
        from_iso: Optional[str],
        to_iso: Optional[str],
        count: int,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"account": account_id, "count": count}
        if from_iso:
            params["from"] = from_iso
        if to_iso:
            params["to"] = to_iso
        data = self._request_json("GET", TRANSACTIONS_PATH, params=params)
        if data is None:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("transactions", "data", "results"):
                inner = data.get(key)
                if isinstance(inner, list):
                    return inner
        raise RevolutApiError("Unexpected transactions response shape")
