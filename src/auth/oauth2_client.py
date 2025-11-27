"""OAuth2 client for Keap API authentication."""
import logging
import requests
import base64
from typing import Dict, Optional, Any
from urllib.parse import urlencode, urlparse, parse_qs

from src.utils.config import get_config
from src.auth.token_manager import TokenManager

logger = logging.getLogger(__name__)


class OAuth2Error(Exception):
    """OAuth2 authentication error."""
    pass


class OAuth2Client:
    """OAuth2 client for Keap API."""
    
    # OAuth2 endpoints
    AUTHORIZATION_URL = "https://accounts.infusionsoft.com/app/oauth/authorize"
    TOKEN_URL = "https://api.infusionsoft.com/token"
    
    def __init__(self, token_manager: Optional[TokenManager] = None):
        """Initialize OAuth2 client.
        
        Args:
            token_manager: TokenManager instance for storing tokens (optional)
        """
        self.config = get_config()
        self.client_id = self.config['keap_client_id']
        self.client_secret = self.config['keap_client_secret']
        self.redirect_uri = self.config['keap_redirect_uri']
        self.token_manager = token_manager
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Generate OAuth2 authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL
        """
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': 'full'
        }
        
        if state:
            params['state'] = state
        
        url = f"{self.AUTHORIZATION_URL}?{urlencode(params)}"
        logger.debug(f"Generated authorization URL: {url}")
        return url
    
    def exchange_code_for_tokens(self, authorization_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens.
        
        Args:
            authorization_code: Authorization code from OAuth2 callback
            
        Returns:
            Dictionary with tokens and metadata
            
        Raises:
            OAuth2Error: If token exchange fails
        """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': authorization_code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        try:
            logger.debug(f"Exchanging authorization code for tokens")
            response = requests.post(self.TOKEN_URL, data=data, headers=headers)
            response.raise_for_status()
            
            token_data = response.json()
            logger.info("Successfully exchanged authorization code for tokens")
            
            # Store tokens if token manager is available
            if self.token_manager:
                expires_in = token_data.get('expires_in', 3600)
                self.token_manager.store_tokens(
                    client_id=self.client_id,
                    access_token=token_data['access_token'],
                    refresh_token=token_data['refresh_token'],
                    expires_in=expires_in,
                    token_type=token_data.get('token_type', 'Bearer'),
                    scope=token_data.get('scope')
                )
            
            return token_data
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error exchanging authorization code: {e}"
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg += f" - {error_data}"
                except:
                    error_msg += f" - {e.response.text}"
            logger.error(error_msg)
            raise OAuth2Error(error_msg) from e
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error exchanging authorization code: {e}"
            logger.error(error_msg)
            raise OAuth2Error(error_msg) from e
        except KeyError as e:
            error_msg = f"Missing required field in token response: {e}"
            logger.error(error_msg)
            raise OAuth2Error(error_msg) from e
    
    def refresh_token(self, refresh_token: str, client_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            client_id: Client ID (uses instance client_id if not provided)
            
        Returns:
            Dictionary with new tokens and metadata, or None if refresh fails
        """
        client_id_to_use = client_id or self.client_id
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        
        # Basic authentication header
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'Authorization': f'Basic {encoded_credentials}'
        }
        
        try:
            logger.debug(f"Refreshing access token for client_id: {client_id_to_use}")
            response = requests.post(self.TOKEN_URL, data=data, headers=headers)
            response.raise_for_status()
            
            token_data = response.json()
            logger.info(f"Successfully refreshed token for client_id: {client_id_to_use}")
            
            # Store new tokens if token manager is available
            if self.token_manager:
                expires_in = token_data.get('expires_in', 3600)
                self.token_manager.store_tokens(
                    client_id=client_id_to_use,
                    access_token=token_data['access_token'],
                    refresh_token=token_data.get('refresh_token', refresh_token),  # Use new refresh token if provided
                    expires_in=expires_in,
                    token_type=token_data.get('token_type', 'Bearer'),
                    scope=token_data.get('scope')
                )
            
            return token_data
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error refreshing token: {e}"
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg += f" - {error_data}"
                    logger.error(error_msg)
                except:
                    error_msg += f" - {e.response.text}"
                    logger.error(error_msg)
            else:
                logger.error(error_msg)
            return None
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error refreshing token: {e}"
            logger.error(error_msg)
            return None
        except Exception as e:
            error_msg = f"Unexpected error refreshing token: {e}"
            logger.error(error_msg)
            return None
    
    def parse_authorization_callback(self, callback_url: str) -> Optional[str]:
        """Parse authorization code from callback URL.
        
        Args:
            callback_url: Full callback URL with query parameters
            
        Returns:
            Authorization code, or None if not found
        """
        try:
            parsed = urlparse(callback_url)
            params = parse_qs(parsed.query)
            
            if 'code' in params:
                code = params['code'][0]
                logger.debug("Extracted authorization code from callback URL")
                return code
            elif 'error' in params:
                error = params['error'][0]
                error_description = params.get('error_description', [''])[0]
                logger.error(f"OAuth2 error in callback: {error} - {error_description}")
                raise OAuth2Error(f"OAuth2 authorization error: {error} - {error_description}")
            else:
                logger.warning("No authorization code or error in callback URL")
                return None
        except Exception as e:
            logger.error(f"Error parsing callback URL: {e}")
            raise OAuth2Error(f"Error parsing callback URL: {e}") from e

