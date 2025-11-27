# 9. Appendix

## 9.1 API Reference

### 9.1.1 Keap API Endpoints
- Base URL: `https://api.infusionsoft.com/crm/rest`
- Authorization: Bearer token in Authorization header
- Rate Limits: See Keap API documentation

### 9.1.2 OAuth2 Endpoints
- Authorization: `https://accounts.infusionsoft.com/app/oauth/authorize`
- Token: `https://api.infusionsoft.com/token`

## 9.2 Entity Types

### 9.2.1 Supported Entities
- Contacts
- Companies
- Opportunities
- Orders
- Products
- Tasks
- Notes
- Campaigns
- Subscriptions
- Affiliates
- Tags
- Custom Fields

### 9.2.2 Entity Relationships
- Contacts → Orders, Opportunities, Tasks, Notes, Subscriptions
- Products → Orders, Subscriptions
- Campaigns → Contacts (via sequences)
- Tags → Contacts (many-to-many)
- Custom Fields → Contacts, Opportunities, Orders, Subscriptions

## 9.3 Error Codes

### 9.3.1 HTTP Status Codes
- 200: Success
- 401: Unauthorized (token expired/invalid)
- 404: Not Found
- 429: Rate Limit Exceeded
- 500: Server Error

### 9.3.2 Application Error Codes
- AUTH_ERROR: Authentication error
- TOKEN_ERROR: Token error
- API_ERROR: API error
- DB_ERROR: Database error
- EXTRACTION_ERROR: Extraction error

## 9.4 Configuration Reference

### 9.4.1 Required Environment Variables
| Variable | Description | Example |
|----------|-------------|---------|
| KEAP_CLIENT_ID | OAuth2 client ID | `abc123...` |
| KEAP_CLIENT_SECRET | OAuth2 client secret | `xyz789...` |
| KEAP_REDIRECT_URI | OAuth2 redirect URI | `https://app.com/callback` |
| DB_HOST | Database host | `localhost` |
| DB_PORT | Database port | `5432` |
| DB_NAME | Database name | `keap_db` |
| DB_USER | Database user | `postgres` |
| DB_PASSWORD | Database password | `secret` |
| TOKEN_ENCRYPTION_KEY | Token encryption key | `32-byte-key` |

### 9.4.2 Optional Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| TOKEN_REFRESH_THRESHOLD | Token refresh threshold (seconds) | `300` |
| LOG_LEVEL | Logging level | `INFO` |
| BATCH_SIZE | Batch size for extraction | `50` |

## 9.5 File Structure

### 9.5.1 Directory Structure
```
keap-data-extract-oauth/
├── src/
│   ├── auth/              # OAuth2 authentication
│   ├── api/               # API client
│   ├── database/          # Database configuration
│   ├── models/            # Database models
│   ├── scripts/           # Data loading scripts
│   ├── transformers/      # Data transformation
│   └── utils/             # Utilities
├── database/
│   └── migrations/        # Database migrations
├── documentation/         # Documentation
├── logs/                  # Application logs
├── checkpoints/           # Extraction checkpoints
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
└── README.md              # Project README
```

### 9.5.2 Key Files
- `src/auth/oauth2_client.py`: OAuth2 client implementation
- `src/auth/token_manager.py`: Token management
- `src/api/base_client.py`: Base API client
- `src/api/keap_client.py`: Keap API client
- `src/scripts/load_data.py`: Main data loading script
- `src/scripts/loaders/`: Entity-specific loaders

## 9.6 Glossary

### 9.6.1 Terms
- **OAuth2**: Open Authorization 2.0 protocol
- **Access Token**: Token used to access API resources
- **Refresh Token**: Token used to obtain new access tokens
- **Authorization Code**: Temporary code exchanged for tokens
- **Checkpoint**: Saved state of extraction progress
- **Incremental Extraction**: Extracting only changed data
- **Entity**: A data type (contact, order, etc.)

### 9.6.2 Acronyms
- **API**: Application Programming Interface
- **OAuth**: Open Authorization
- **HTTPS**: Hypertext Transfer Protocol Secure
- **JSON**: JavaScript Object Notation
- **REST**: Representational State Transfer
- **SQL**: Structured Query Language

## 9.7 References

### 9.7.1 Documentation
- [Keap REST API Documentation](https://developer.keap.com/docs/rest/)
- [Keap OAuth2 Guide](https://developer.infusionsoft.com/getting-started-oauth-keys/)
- [OAuth2 Specification](https://oauth.net/2/)

### 9.7.2 Libraries
- [Requests](https://requests.readthedocs.io/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Alembic](https://alembic.sqlalchemy.org/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)

## 9.8 Change Log

### 9.8.1 Version History
- **v1.0.0** (Planned): Initial OAuth2 implementation
  - OAuth2 authentication
  - Token management
  - Enhanced checkpoint system
  - Incremental extraction support

## 9.9 Support and Contact

### 9.9.1 Getting Help
- Review documentation
- Check error logs
- Review Keap API documentation
- Contact development team

### 9.9.2 Reporting Issues
- Create issue in repository
- Include error logs
- Include configuration (without secrets)
- Describe steps to reproduce

