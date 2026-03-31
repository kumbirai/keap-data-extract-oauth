"""
Revolut Business API 1.0 paths and OAuth defaults.

Verified against public Revolut developer materials (Business API guides, community examples).
Confirm details at https://developer.revolut.com/docs/business/business-api/ when Revolut changes APIs.
"""

# API version prefix (all resource paths are relative to this base).
API_PREFIX = "/api/1.0"

# Resource paths (relative to host root, includes API_PREFIX).
ACCOUNTS_PATH = f"{API_PREFIX}/accounts"
TRANSACTIONS_PATH = f"{API_PREFIX}/transactions"
TOKEN_PATH = f"{API_PREFIX}/auth/token"

# Production and sandbox hosts (scheme + host only; paths appended in client).
PRODUCTION_HOST = "https://b2b.revolut.com"
SANDBOX_HOST = "https://sandbox-b2b.revolut.com"

# OAuth 2.0 client authentication (JWT bearer client assertion).
CLIENT_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"

# JWT signing for client assertion (Revolut Business API).
JWT_ALGORITHM = "PS256"
# Default audience; override with REVOLUT_JWT_AUDIENCE if token exchange fails.
DEFAULT_JWT_AUDIENCE = "https://revolut.com"

# Client assertion JWT lifetime (seconds). Keep short per security guidance.
DEFAULT_ASSERTION_TTL_SECONDS = 60 * 10

# Token refresh: refresh access a bit before expiry.
TOKEN_EXPIRY_SKEW_SECONDS = 120

# Transactions list: max page size per Revolut docs (cap requests).
DEFAULT_TRANSACTION_PAGE_SIZE = 500
MAX_TRANSACTION_PAGE_SIZE = 1000

# HTTP retry (429 / 5xx).
DEFAULT_MAX_HTTP_ATTEMPTS = 6
DEFAULT_BACKOFF_INITIAL_SECONDS = 1.0
DEFAULT_BACKOFF_MAX_SECONDS = 60.0
