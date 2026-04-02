"""Base API client with OAuth2 authentication."""
import logging
from typing import Any, Dict, Optional

import requests

from .exceptions import KeapAuthenticationError
from .keap_http import handle_keap_response, safe_int_parse as _safe_int_parse, has_meaningful_value as _http_has_meaningful_value
from ..auth.token_manager import TokenManager
from ..utils.config import get_config

logger = logging.getLogger(__name__)


class KeapBaseClient:
    """Base client for Keap API with OAuth2 authentication."""
    
    def __init__(self, token_manager: TokenManager):
        """Initialize base API client.
        
        Args:
            token_manager: TokenManager instance for OAuth2 token management
        """
        self.base_url = "https://api.infusionsoft.com/crm/rest/v1"
        self.token_manager = token_manager
        self.config = get_config()
        self.client_id = self.config['keap_client_id']
        
        # Initialize session for connection pooling
        self.session = requests.Session()
        self._update_headers()
        
        logger.info("KeapBaseClient initialized")
        logger.info(f"Using base URL: {self.base_url}")
    
    def _update_headers(self):
        """Update session headers with current access token."""
        try:
            access_token = self.token_manager.get_valid_access_token(self.client_id)
        except Exception as e:
            # Check if it's a database table error
            error_str = str(e).lower()
            if 'does not exist' in error_str or 'relation' in error_str or 'table' in error_str:
                raise KeapAuthenticationError(
                    "Database tables not found. Please run database migrations first:\n"
                    "  alembic upgrade head\n"
                    "Then authorize the application:\n"
                    "  python -m src.auth.authorize"
                ) from e
            raise KeapAuthenticationError(f"Error retrieving access token: {e}") from e
        
        if not access_token:
            raise KeapAuthenticationError(
                "No valid access token available. Please authorize the application:\n"
                "  python -m src.auth.authorize"
            )
        
        self.headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        self.session.headers.update(self.headers)
    
    @staticmethod
    def safe_int_parse(value, default=0):
        return _safe_int_parse(value, default)

    @staticmethod
    def has_meaningful_value(value):
        return _http_has_meaningful_value(value)

    def _handle_response(self, response: requests.Response) -> Dict:
        return handle_keap_response(
            response,
            token_manager=self.token_manager,
            client_id=self.client_id,
            refresh_headers=self._update_headers,
        )

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, retry_on_401: bool = True) -> Dict:
        """
        Make an HTTP request to the Keap API with automatic token refresh
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            retry_on_401: Whether to retry on 401 after token refresh
            
        Returns:
            Dict containing the API response
            
        Raises:
            KeapAPIError: If the request fails after all retries
        """
        url = f"{self.base_url}/{endpoint}"

        try:
            logger.debug(f"Making {method} request to {url}")
            response = self.session.request(method=method, url=url, params=params)
            logger.debug(f"Response status: {response.status_code}")
            
            # Handle 401 with token refresh and retry
            if response.status_code == 401 and retry_on_401:
                logger.warning("Received 401, refreshing token and retrying...")
                if self.token_manager.refresh_access_token(self.client_id):
                    self._update_headers()
                    # Retry the request once
                    response = self.session.request(method=method, url=url, params=params)
                    logger.debug(f"Retry response status: {response.status_code}")
                else:
                    logger.error("Failed to refresh token")
            
            return self._handle_response(response)
        except KeapAuthenticationError:
            # Re-raise authentication errors
            raise
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            raise

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict:
        """
        Make a GET request to the Keap API
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Dict containing the API response
            
        Raises:
            KeapAPIError: If the request fails after all retries
        """
        return self._make_request('GET', endpoint, params)

    def __del__(self):
        """Cleanup session on object destruction"""
        if hasattr(self, 'session'):
            self.session.close()

