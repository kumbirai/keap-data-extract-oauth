"""Token storage with encryption for OAuth2 tokens."""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import os

from src.models.oauth_models import OAuthToken
from src.utils.config import get_env_var

logger = logging.getLogger(__name__)


class TokenStorage:
    """Secure token storage with encryption."""
    
    def __init__(self, db_session: Session):
        """Initialize token storage.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self._cipher = self._create_cipher()
    
    def _create_cipher(self) -> Fernet:
        """Create Fernet cipher from encryption key.
        
        Returns:
            Fernet cipher instance
        """
        encryption_key = get_env_var('TOKEN_ENCRYPTION_KEY')
        
        # Ensure key is exactly 32 bytes for Fernet
        if len(encryption_key) < 32:
            # Pad with zeros if too short (not ideal but works)
            encryption_key = encryption_key.ljust(32, '0')
        elif len(encryption_key) > 32:
            # Truncate if too long
            encryption_key = encryption_key[:32]
        
        # Convert to bytes and create Fernet key
        key_bytes = encryption_key.encode('utf-8')
        
        # Use PBKDF2 to derive a proper Fernet key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'keap_token_storage',  # Fixed salt for consistency
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(key_bytes))
        
        return Fernet(key)
    
    def _encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext token.
        
        Args:
            plaintext: Plaintext token to encrypt
            
        Returns:
            Encrypted token as base64 string
        """
        if not plaintext:
            return ""
        encrypted = self._cipher.encrypt(plaintext.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted).decode('utf-8')
    
    def _decrypt(self, ciphertext: str) -> str:
        """Decrypt encrypted token.
        
        Args:
            ciphertext: Encrypted token as base64 string
            
        Returns:
            Decrypted plaintext token
        """
        if not ciphertext:
            return ""
        encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode('utf-8'))
        decrypted = self._cipher.decrypt(encrypted_bytes)
        return decrypted.decode('utf-8')
    
    def store_tokens(
        self,
        client_id: str,
        access_token: str,
        refresh_token: str,
        expires_at: datetime,
        token_type: str = 'Bearer',
        scope: Optional[str] = None
    ) -> OAuthToken:
        """Store OAuth2 tokens with encryption.
        
        Args:
            client_id: OAuth2 client ID
            access_token: Access token to store
            refresh_token: Refresh token to store
            expires_at: Token expiration datetime
            token_type: Token type (default: Bearer)
            scope: OAuth2 scope
            
        Returns:
            OAuthToken instance
            
        Raises:
            ValueError: If required parameters are invalid
            Exception: If database operation fails
        """
        # Input validation
        if not client_id or not isinstance(client_id, str):
            raise ValueError("client_id must be a non-empty string")
        if not access_token or not isinstance(access_token, str):
            raise ValueError("access_token must be a non-empty string")
        if not refresh_token or not isinstance(refresh_token, str):
            raise ValueError("refresh_token must be a non-empty string")
        if not isinstance(expires_at, datetime):
            raise ValueError("expires_at must be a datetime object")
        
        try:
            # Encrypt tokens
            access_token_encrypted = self._encrypt(access_token)
            refresh_token_encrypted = self._encrypt(refresh_token)
            
            # Check if token already exists
            existing = self.db.query(OAuthToken).filter_by(client_id=client_id).first()
            
            if existing:
                # Update existing token
                existing.access_token_encrypted = access_token_encrypted
                existing.refresh_token_encrypted = refresh_token_encrypted
                existing.token_type = token_type
                existing.expires_at = expires_at
                existing.scope = scope
                existing.updated_at = datetime.now(timezone.utc)
                self.db.commit()
                logger.info(f"Updated tokens for client_id: {client_id}")
                return existing
            else:
                # Create new token
                token = OAuthToken(
                    client_id=client_id,
                    access_token_encrypted=access_token_encrypted,
                    refresh_token_encrypted=refresh_token_encrypted,
                    token_type=token_type,
                    expires_at=expires_at,
                    scope=scope
                )
                self.db.add(token)
                self.db.commit()
                logger.info(f"Stored new tokens for client_id: {client_id}")
                return token
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error storing tokens for client_id {client_id}: {e}")
            raise
    
    def get_tokens(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt OAuth2 tokens.
        
        Args:
            client_id: OAuth2 client ID
            
        Returns:
            Dictionary with tokens and metadata, or None if not found
            
        Raises:
            ValueError: If client_id is invalid
            Exception: If database table doesn't exist (migrations not run)
        """
        if not client_id or not isinstance(client_id, str):
            raise ValueError("client_id must be a non-empty string")
        
        try:
            token = self.db.query(OAuthToken).filter_by(client_id=client_id).first()
            
            if not token:
                logger.debug(f"No tokens found for client_id: {client_id}")
                return None
            
            # Decrypt tokens
            access_token = self._decrypt(token.access_token_encrypted)
            refresh_token = self._decrypt(token.refresh_token_encrypted)
            
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': token.token_type,
                'expires_at': token.expires_at,
                'scope': token.scope,
                'created_at': token.created_at,
                'updated_at': token.updated_at
            }
        except Exception as e:
            error_str = str(e).lower()
            # Check if it's a database table error
            if 'does not exist' in error_str or 'relation' in error_str or 'table' in error_str:
                logger.error(f"Database table 'oauth_tokens' does not exist. Please run migrations first.")
                # Re-raise with more context
                raise Exception(
                    "Database tables not found. Please run database migrations first:\n"
                    "  alembic upgrade head"
                ) from e
            logger.error(f"Error retrieving/decrypting tokens for client_id {client_id}: {e}")
            return None
    
    def update_tokens(
        self,
        client_id: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        token_type: Optional[str] = None,
        scope: Optional[str] = None
    ) -> Optional[OAuthToken]:
        """Update existing tokens.
        
        Args:
            client_id: OAuth2 client ID
            access_token: New access token (optional)
            refresh_token: New refresh token (optional)
            expires_at: New expiration datetime (optional)
            token_type: New token type (optional)
            scope: New scope (optional)
            
        Returns:
            Updated OAuthToken instance, or None if not found
            
        Raises:
            ValueError: If client_id is invalid
            Exception: If database operation fails
        """
        if not client_id or not isinstance(client_id, str):
            raise ValueError("client_id must be a non-empty string")
        
        try:
            token = self.db.query(OAuthToken).filter_by(client_id=client_id).first()
            
            if not token:
                logger.warning(f"No tokens found to update for client_id: {client_id}")
                return None
            
            # Update only provided fields
            if access_token is not None:
                if not isinstance(access_token, str):
                    raise ValueError("access_token must be a string")
                token.access_token_encrypted = self._encrypt(access_token)
            if refresh_token is not None:
                if not isinstance(refresh_token, str):
                    raise ValueError("refresh_token must be a string")
                token.refresh_token_encrypted = self._encrypt(refresh_token)
            if expires_at is not None:
                if not isinstance(expires_at, datetime):
                    raise ValueError("expires_at must be a datetime object")
                token.expires_at = expires_at
            if token_type is not None:
                token.token_type = token_type
            if scope is not None:
                token.scope = scope
            
            token.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            logger.info(f"Updated tokens for client_id: {client_id}")
            return token
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating tokens for client_id {client_id}: {e}")
            raise
    
    def delete_tokens(self, client_id: str) -> bool:
        """Delete tokens for a client.
        
        Args:
            client_id: OAuth2 client ID
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            ValueError: If client_id is invalid
            Exception: If database operation fails
        """
        if not client_id or not isinstance(client_id, str):
            raise ValueError("client_id must be a non-empty string")
        
        try:
            token = self.db.query(OAuthToken).filter_by(client_id=client_id).first()
            
            if not token:
                logger.debug(f"No tokens found to delete for client_id: {client_id}")
                return False
            
            self.db.delete(token)
            self.db.commit()
            logger.info(f"Deleted tokens for client_id: {client_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting tokens for client_id {client_id}: {e}")
            raise

