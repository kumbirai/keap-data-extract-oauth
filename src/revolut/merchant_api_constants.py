"""
Revolut Merchant API paths and defaults.

See documentation/revolut/sprint-02/ for design context.
Verify endpoint paths and version strings against https://developer.revolut.com/docs/merchant/merchant-api.
"""

# Merchant API version header value.
DEFAULT_API_VERSION = "2024-09-01"

# Resource path prefix (all paths are relative to the host root).
API_PREFIX = "/api"

# Resource paths (includes API_PREFIX).
ORDERS_PATH = f"{API_PREFIX}/orders"
CUSTOMERS_PATH = f"{API_PREFIX}/customers"
DISPUTES_PATH = f"{API_PREFIX}/disputes"
LOCATIONS_PATH = f"{API_PREFIX}/locations"

# Per-order and per-customer sub-resource paths (format strings).
ORDER_PAYMENTS_PATH = f"{API_PREFIX}/orders/{{order_id}}/payments"
CUSTOMER_PAYMENT_METHODS_PATH = f"{API_PREFIX}/customers/{{customer_id}}/payment-methods"

# Production and sandbox hosts.
PRODUCTION_HOST = "https://merchant.revolut.com"
SANDBOX_HOST = "https://sandbox-merchant.revolut.com"

# Default page size for list endpoints.
DEFAULT_PAGE_SIZE = 100

# HTTP retry (429 / 5xx).
DEFAULT_MAX_HTTP_ATTEMPTS = 6
DEFAULT_BACKOFF_INITIAL_SECONDS = 1.0
DEFAULT_BACKOFF_MAX_SECONDS = 60.0
