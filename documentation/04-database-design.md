# 4. Database Design

## 4.1 Database Schema

### 4.1.1 OAuth Token Storage

```sql
CREATE TABLE oauth_tokens (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(255) NOT NULL UNIQUE,
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT NOT NULL,
    token_type VARCHAR(50) DEFAULT 'Bearer',
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    scope VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_oauth_tokens_client_id ON oauth_tokens(client_id);
CREATE INDEX idx_oauth_tokens_expires_at ON oauth_tokens(expires_at);
```

### 4.1.2 Extraction State Tracking

```sql
CREATE TABLE extraction_state (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(100) NOT NULL UNIQUE,
    total_records_processed INTEGER DEFAULT 0,
    api_offset INTEGER DEFAULT 0,
    last_loaded TIMESTAMP WITH TIME ZONE,
    last_successful_extraction TIMESTAMP WITH TIME ZONE,
    extraction_status VARCHAR(50) DEFAULT 'pending',
    error_count INTEGER DEFAULT 0,
    last_error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_extraction_state_entity_type ON extraction_state(entity_type);
CREATE INDEX idx_extraction_state_status ON extraction_state(extraction_status);
```

### 4.1.3 Existing Entity Tables
The existing database schema from the previous implementation will be maintained:
- `contacts` and related tables
- `orders`, `order_items`, `order_payments`, `order_transactions`
- `products`, `subscription_plans`
- `opportunities`
- `tasks`
- `notes`
- `campaigns`, `campaign_sequences`
- `subscriptions`
- `affiliates` and related affiliate tables
- `tags`, `tag_categories`
- `custom_fields` and custom field value tables
- `account_profiles`, `business_goals`

## 4.2 Token Encryption

### 4.2.1 Encryption Strategy
- Use AES-256 encryption for token storage
- Encryption key stored in environment variable
- Tokens encrypted before database storage
- Tokens decrypted when retrieved

### 4.2.2 Encryption Implementation
- Use `cryptography` library for encryption
- Generate encryption key from environment variable
- Store encrypted tokens in database
- Decrypt tokens in memory only

## 4.3 Database Migrations

### 4.3.1 Migration Strategy
- Use Alembic for database migrations
- Create migration for OAuth token table
- Create migration for extraction state table
- Maintain backward compatibility

### 4.3.2 Migration Files
- `001_add_oauth_tokens_table.py`
- `002_add_extraction_state_table.py`
- Future migrations as needed

## 4.4 Connection Management

### 4.4.1 Connection Pooling
- Use SQLAlchemy connection pooling
- Pool size: 5 connections
- Max overflow: 10 connections
- Pool timeout: 30 seconds
- Pool recycle: 1800 seconds (30 minutes)

### 4.4.2 Session Management
- Use session factory for database sessions
- Context managers for session lifecycle
- Automatic session cleanup
- Transaction management

## 4.5 Data Integrity

### 4.5.1 Foreign Key Constraints
- Maintain all existing foreign key relationships
- Ensure referential integrity
- Handle cascading deletes appropriately

### 4.5.2 Unique Constraints
- Maintain unique constraints on entity IDs
- Prevent duplicate records
- Handle upsert operations

### 4.5.3 Indexes
- Maintain existing indexes for performance
- Add indexes for new tables
- Monitor index usage and optimize

## 4.6 Backup and Recovery

### 4.6.1 Backup Strategy
- Regular database backups
- Transaction log backups
- Point-in-time recovery capability

### 4.6.2 Recovery Procedures
- Restore from backup if needed
- Replay transaction logs
- Verify data integrity after recovery

