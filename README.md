# Keap Data Extractor - OAuth2

A production-grade Python application for extracting data from the Keap API using OAuth2 authentication. This application supports resumable data extraction with checkpoint tracking and incremental updates for changed data only.

## Features

- **OAuth2 Authentication**: Secure OAuth2 implementation with automatic token refresh
- **Resumable Extraction**: Checkpoint system allows extraction to resume after interruption
- **Incremental Updates**: Extract only changed data since last run using `since` parameter
- **Comprehensive Data Extraction**: Extract contacts, orders, products, opportunities, tasks, notes, campaigns, subscriptions, affiliates, tags, and custom fields
- **Error Handling**: Robust error handling with automatic retry and error reprocessing
- **Production Ready**: Comprehensive logging, monitoring, and audit trails

## Prerequisites

- Python 3.8 or higher
- PostgreSQL database (version 12 or higher)
- Keap OAuth2 credentials (client_id, client_secret)
- Access to Keap Developer Portal

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd keap-data-extract-oauth
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Set up the database:
```bash
createdb keap_db
alembic upgrade head
```

6. Authorize the application:
```bash
python src/auth/authorize.py
```

## Configuration

Required environment variables (see `.env.example`):

- `KEAP_CLIENT_ID`: Your OAuth2 client ID from Keap Developer Portal
- `KEAP_CLIENT_SECRET`: Your OAuth2 client secret
- `KEAP_REDIRECT_URI`: OAuth2 redirect URI (must be HTTPS)
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`: Database connection settings
- `TOKEN_ENCRYPTION_KEY`: 32-byte encryption key for token storage

## Usage

### Full Data Extraction
```bash
python -m src
```

### Incremental Update (only changed data)
```bash
python -m src --update
```

### Extract Specific Entity Type
```bash
python -m src --entity-type contacts
```

### Extract Single Entity
```bash
python -m src --entity-type contacts --entity-id 123
```

## OAuth2 Authorization

Before first use, you must authorize the application:

1. Run the authorization tool:
```bash
python src/auth/authorize.py
```

2. Follow the prompts to complete OAuth2 authorization
3. Tokens will be stored securely in the database

## Project Structure

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
│   └── migrations/       # Alembic migrations
├── documentation/         # Project documentation
├── logs/                 # Application logs
└── checkpoints/          # Extraction checkpoints
```

## Documentation

See the `documentation/` directory for comprehensive documentation including:
- Project overview and architecture
- OAuth2 authentication design
- Data extraction design
- Database schema
- Implementation phases
- Security considerations
- Testing strategy
- Deployment guide

## License

[Add your license here]

## Support

For issues and questions, please refer to the documentation or open an issue in the repository.

