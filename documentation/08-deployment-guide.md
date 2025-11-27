# 8. Deployment Guide

## 8.1 Prerequisites

### 8.1.1 System Requirements
- **Python**: 3.8 or higher
- **PostgreSQL**: 12 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 2GB RAM
- **Disk Space**: Minimum 10GB free space

### 8.1.2 Required Accounts
- **Keap Developer Account**: For OAuth2 credentials
- **Database Access**: PostgreSQL database access
- **Network Access**: Internet access for API calls

## 8.2 Installation Steps

### 8.2.1 Clone Repository
```bash
git clone <repository-url>
cd keap-data-extract-oauth
```

### 8.2.2 Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 8.2.3 Install Dependencies
```bash
pip install -r requirements.txt
```

### 8.2.4 Database Setup
```bash
# Create database
createdb keap_db

# Run migrations
alembic upgrade head
```

### 8.2.5 Configuration
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
# Required variables:
# - KEAP_CLIENT_ID
# - KEAP_CLIENT_SECRET
# - KEAP_REDIRECT_URI
# - DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
# - TOKEN_ENCRYPTION_KEY
```

## 8.3 OAuth2 Setup

### 8.3.1 Register Application
1. Log in to Keap Developer Portal
2. Create new application
3. Configure redirect URI (must be HTTPS)
4. Obtain client_id and client_secret

### 8.3.2 Initial Authorization
1. Run authorization script:
```bash
python src/auth/authorize.py
```
2. Follow prompts to authorize application
3. Tokens will be stored automatically

## 8.4 Configuration

### 8.4.1 Environment Variables
```bash
# OAuth2 Configuration
KEAP_CLIENT_ID=your_client_id
KEAP_CLIENT_SECRET=your_client_secret
KEAP_REDIRECT_URI=https://your-app.com/oauth/callback

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=keap_db
DB_USER=postgres
DB_PASSWORD=your_password

# Token Encryption
TOKEN_ENCRYPTION_KEY=your_encryption_key

# Optional Configuration
TOKEN_REFRESH_THRESHOLD=300
LOG_LEVEL=INFO
BATCH_SIZE=50
```

### 8.4.2 Configuration Validation
```bash
# Validate configuration
python src/utils/validate_config.py
```

## 8.5 Running the Application

### 8.5.1 Full Data Extraction
```bash
python -m src
```

### 8.5.2 Incremental Update
```bash
python -m src --update
```

### 8.5.3 Extract Specific Entity
```bash
python -m src --entity-type contacts
```

### 8.5.4 Extract Single Entity
```bash
python -m src --entity-type contacts --entity-id 123
```

## 8.6 Production Deployment

### 8.6.1 Security Considerations
- Use strong encryption keys
- Secure database credentials
- Use HTTPS for redirect URI
- Implement proper access controls
- Enable logging and monitoring

### 8.6.2 Process Management
- Use process manager (systemd, supervisor, etc.)
- Implement auto-restart on failure
- Monitor resource usage
- Set up log rotation

### 8.6.3 Monitoring
- Set up application monitoring
- Monitor database performance
- Track API usage and quotas
- Alert on errors

## 8.7 Maintenance

### 8.7.1 Regular Tasks
- Monitor extraction logs
- Check for errors
- Verify data integrity
- Review performance metrics

### 8.7.2 Updates
- Keep dependencies updated
- Apply security patches
- Update application code
- Test updates in staging

### 8.7.3 Backup
- Regular database backups
- Backup checkpoint files
- Backup configuration
- Test backup restoration

## 8.8 Troubleshooting

### 8.8.1 Common Issues
- **Token Expiration**: Re-authorize application
- **Database Connection**: Check database credentials
- **API Errors**: Check API status and quotas
- **Extraction Errors**: Review error logs

### 8.8.2 Logs
- Application logs: `logs/keap_data_extract_*.log`
- Error logs: `logs/errors/`
- Audit logs: `logs/audit_log.json`

### 8.8.3 Support
- Check documentation
- Review error logs
- Check Keap API status
- Contact support if needed

