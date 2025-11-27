# 2. OAuth2 Authentication Design

## 2.1 OAuth2 Flow Overview

The application will implement the OAuth2 Authorization Code Grant flow with Refresh Token rotation as specified in the Keap OAuth2 documentation.

### 2.1.1 Flow Steps
1. **Authorization Request**: Redirect user to Keap authorization endpoint
2. **User Authorization**: User logs in and grants permissions
3. **Authorization Code**: Keap redirects back with authorization code
4. **Token Exchange**: Exchange authorization code for access token and refresh token
5. **API Access**: Use access token for API requests
6. **Token Refresh**: Automatically refresh tokens when they expire

## 2.2 OAuth2 Endpoints

### 2.2.1 Authorization Endpoint
- **URL**: `https://accounts.infusionsoft.com/app/oauth/authorize`
- **Method**: GET (redirect)
- **Parameters**:
  - `client_id`: Application client ID
  - `redirect_uri`: Callback URL (must be HTTPS)
  - `response_type`: Always `code`
  - `scope`: Always `full`

### 2.2.2 Token Endpoint
- **URL**: `https://api.infusionsoft.com/token`
- **Method**: POST
- **Content-Type**: `application/x-www-form-urlencoded`
- **Parameters**:
  - For authorization code exchange:
    - `client_id`: Application client ID
    - `client_secret`: Application client secret
    - `code`: Authorization code from callback
    - `grant_type`: `authorization_code`
    - `redirect_uri`: Same redirect URI used in authorization request
  - For token refresh:
    - `grant_type`: `refresh_token`
    - `refresh_token`: Current refresh token
    - `Authorization`: Basic auth header (base64(client_id:client_secret))

## 2.3 Token Management

### 2.3.1 Token Storage
Tokens will be stored securely in the database with the following schema:

```sql
CREATE TABLE oauth_tokens (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_type VARCHAR(50) DEFAULT 'Bearer',
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    scope VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(client_id)
);
```

### 2.3.2 Token Refresh Strategy
- **Automatic Refresh**: Tokens will be refreshed automatically before expiration
- **Refresh Threshold**: Refresh when token expires within 5 minutes
- **Refresh on 401**: If API returns 401, attempt token refresh and retry request
- **Token Rotation**: Store new refresh token after each refresh (Keap rotates refresh tokens)

### 2.3.3 Token Security
- Store tokens encrypted in database
- Never log tokens in plain text
- Use secure storage for client credentials
- Implement token rotation handling

## 2.4 Implementation Components

### 2.4.1 OAuth2Client
Responsible for:
- Generating authorization URLs
- Handling authorization callbacks
- Exchanging authorization codes for tokens
- Refreshing access tokens

### 2.4.2 TokenManager
Responsible for:
- Storing and retrieving tokens
- Checking token expiration
- Triggering token refresh
- Handling token rotation

### 2.4.3 TokenStorage
Responsible for:
- Database operations for token storage
- Token encryption/decryption
- Token retrieval by client_id

## 2.5 Authorization Flow Implementation

### 2.5.1 Initial Authorization
1. User initiates authorization
2. Application generates authorization URL
3. User is redirected to Keap
4. User authorizes application
5. Keap redirects to callback URL with code
6. Application exchanges code for tokens
7. Tokens are stored in database

### 2.5.2 Subsequent API Calls
1. Application retrieves stored tokens
2. Check if access token is expired or near expiration
3. If expired, refresh using refresh token
4. Use access token in Authorization header: `Bearer {access_token}`
5. Make API request

## 2.6 Error Handling

### 2.6.1 Token Errors
- **Invalid Grant**: Re-authenticate user
- **Expired Refresh Token**: Re-authenticate user
- **Invalid Token**: Refresh token and retry
- **Token Not Found**: Initiate authorization flow

### 2.6.2 API Errors
- **401 Unauthorized**: Refresh token and retry request
- **403 Forbidden**: Log error, may need re-authorization
- **429 Rate Limit**: Handle rate limiting (existing logic)

## 2.7 Configuration

### 2.7.1 Required Environment Variables
```bash
# OAuth2 Configuration
KEAP_CLIENT_ID=your_client_id
KEAP_CLIENT_SECRET=your_client_secret
KEAP_REDIRECT_URI=https://your-app.com/oauth/callback

# Token Storage
TOKEN_ENCRYPTION_KEY=your_encryption_key  # For encrypting tokens in DB
```

### 2.7.2 Optional Configuration
```bash
# Token Refresh Settings
TOKEN_REFRESH_THRESHOLD=300  # Refresh if expires within 5 minutes (seconds)
TOKEN_STORAGE_BACKEND=database  # Options: database, file, memory
```

