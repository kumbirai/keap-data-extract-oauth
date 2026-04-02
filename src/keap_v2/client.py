"""HTTP client for Keap REST v2 (cursor pagination, shared error handling)."""
import logging
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests

from src.api.keap_http import handle_keap_response
from src.api.exceptions import KeapAuthenticationError
from src.auth.token_manager import TokenManager
from src.utils.config import get_config

from .settings import KeapV2ExtractSettings

logger = logging.getLogger(__name__)


class KeapV2Client:
    """GET requests under `{crm_base}/rest/v2/...` with the same OAuth token as v1."""

    def __init__(
        self,
        token_manager: TokenManager,
        settings: Optional[KeapV2ExtractSettings] = None,
    ):
        self.token_manager = token_manager
        self.config = get_config()
        self.client_id = self.config["keap_client_id"]
        self._settings = settings or KeapV2ExtractSettings.from_env()
        self.crm_base_url = self._settings.crm_base_url
        self.session = requests.Session()
        self._update_headers()
        logger.info("KeapV2Client initialized; CRM base URL: %s", self.crm_base_url)

    def _update_headers(self) -> None:
        try:
            access_token = self.token_manager.get_valid_access_token(self.client_id)
        except Exception as e:
            error_str = str(e).lower()
            if "does not exist" in error_str or "relation" in error_str or "table" in error_str:
                raise KeapAuthenticationError(
                    "Database tables not found. Run: alembic upgrade head\n"
                    "Then: python -m src.auth.authorize"
                ) from e
            raise KeapAuthenticationError(f"Error retrieving access token: {e}") from e
        if not access_token:
            raise KeapAuthenticationError(
                "No valid access token. Authorize: python -m src.auth.authorize"
            )
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
        )

    def _v2_url(self, resource_path: str) -> str:
        path = resource_path.lstrip("/")
        base = self.crm_base_url.rstrip("/") + "/"
        return urljoin(base, f"rest/v2/{path}")

    def get(self, resource_path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET a v2 resource path (e.g. ``companies`` or ``contacts/123/links``)."""
        url = self._v2_url(resource_path)
        logger.debug("Keap v2 GET %s params=%s", url, params)
        response = self.session.request(method="GET", url=url, params=params or {})
        if response.status_code == 401:
            logger.warning("Keap v2: 401, refreshing token and retrying once...")
            if self.token_manager.refresh_access_token(self.client_id):
                self._update_headers()
                response = self.session.request(method="GET", url=url, params=params or {})
            else:
                logger.error("Keap v2: token refresh failed")
        return handle_keap_response(
            response,
            token_manager=self.token_manager,
            client_id=self.client_id,
            refresh_headers=self._update_headers,
        )

    def close(self) -> None:
        if hasattr(self, "session"):
            self.session.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
