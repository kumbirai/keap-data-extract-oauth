# 3. Data Extraction Design

## 3.1 Extraction Architecture

The data extraction system will maintain the existing architecture while adapting it for OAuth2 authentication. The core extraction logic remains the same, with authentication handled transparently by the OAuth2 client.

### 3.1.1 Extraction Flow
1. Initialize OAuth2 client and authenticate
2. Load checkpoint state (if exists)
3. Determine extraction mode (full or incremental)
4. Extract entities in dependency order
5. Save checkpoints after each batch
6. Handle errors and retries
7. Update last extraction timestamp

## 3.2 Checkpoint System

### 3.2.1 Checkpoint Structure
Checkpoints track extraction progress for each entity type:

```json
{
  "entity_type": {
    "total_records_processed": 0,
    "api_offset": 0,
    "last_loaded": "2024-01-01T00:00:00Z",
    "last_successful_extraction": "2024-01-01T00:00:00Z",
    "extraction_status": "completed|in_progress|failed"
  }
}
```

### 3.2.2 Checkpoint Storage
- **Location**: `checkpoints/extraction_state.json`
- **Format**: JSON
- **Persistence**: Saved after each batch
- **Recovery**: Loaded on application start

### 3.2.3 Checkpoint Usage
- **Resume Point**: Track where extraction stopped
- **Incremental Updates**: Use `last_loaded` timestamp for `since` parameter
- **Progress Tracking**: Monitor extraction progress
- **Error Recovery**: Identify failed extractions

## 3.3 Incremental Extraction

### 3.3.1 Incremental Update Strategy
- Use `since` parameter in API requests
- Filter by `last_loaded` timestamp from checkpoint
- Only fetch records modified since last extraction
- Update checkpoints with new `last_loaded` timestamp

### 3.3.2 Supported Entity Types
All entity types that support the `since` parameter:
- Contacts
- Opportunities
- Orders
- Tasks
- Notes
- Campaigns
- Subscriptions
- Products
- Affiliates
- Tags

### 3.3.3 Incremental Extraction Flow
1. Load checkpoint for entity type
2. Get `last_loaded` timestamp
3. Make API request with `since={last_loaded}`
4. Process returned records
5. Update checkpoint with new timestamp
6. Continue until no more records

## 3.4 Entity Loading Order

### 3.4.1 Dependency Order
Entities must be loaded in a specific order to maintain referential integrity:

1. **Custom Fields** - Required for other entities
2. **Tags** - Required for contact tagging
3. **Products** - Required for orders
4. **Contacts** - Base entity for many relationships
5. **Opportunities** - Depends on contacts
6. **Affiliates** - Depends on contacts
7. **Orders** - Depends on contacts and products
8. **Tasks** - Depends on contacts
9. **Notes** - Depends on contacts
10. **Campaigns** - Standalone but may reference contacts
11. **Subscriptions** - Depends on contacts and products

### 3.4.2 Parallel Extraction
- Independent entities can be extracted in parallel
- Dependent entities must wait for dependencies
- Use dependency graph to determine parallelization opportunities

## 3.5 Error Handling and Recovery

### 3.5.1 Error Categories
1. **Transient Errors**: Network issues, rate limits
   - Strategy: Retry with exponential backoff
2. **Authentication Errors**: Token expiration, invalid tokens
   - Strategy: Refresh token and retry
3. **Data Errors**: Missing dependencies, invalid data
   - Strategy: Log error, skip record, reprocess later
4. **Fatal Errors**: Quota exhaustion, API changes
   - Strategy: Stop extraction, log error, alert

### 3.5.2 Retry Strategy
- **Max Retries**: 5 attempts
- **Base Delay**: 1 second
- **Max Delay**: 60 seconds
- **Exponential Backoff**: 2.0
- **Jitter**: Enabled to prevent thundering herd

### 3.5.3 Error Logging
- Structured error logs in `logs/errors/`
- JSON format for easy parsing
- Include entity type, ID, error type, message
- Track retry attempts and outcomes

### 3.5.4 Error Reprocessing
- Failed entities logged for later reprocessing
- Automatic reprocessing after dependencies loaded
- Manual reprocessing via command-line tool
- Track reprocessing attempts and outcomes

## 3.6 Rate Limiting and Quota Management

### 3.6.1 Rate Limit Detection
- Monitor response headers for rate limit information
- Track quota and throttle limits
- Implement backoff when limits approached

### 3.6.2 Quota Headers
- `x-keap-product-quota-limit`: Daily quota limit
- `x-keap-product-quota-used`: Quota used
- `x-keap-product-quota-available`: Quota remaining
- `x-keap-product-throttle-available`: Throttle remaining

### 3.6.3 Rate Limit Handling
- **429 Response**: Wait and retry
- **Quota Exhausted**: Stop extraction, log error
- **Throttle Limit**: Implement backoff, continue after delay

## 3.7 Batch Processing

### 3.7.1 Batch Size
- Default: 50 records per batch
- Configurable via environment variable
- Adjust based on API limits and performance

### 3.7.2 Batch Processing Flow
1. Fetch batch from API
2. Process each record in batch
3. Save checkpoint after batch
4. Continue to next batch
5. Handle errors per record

### 3.7.3 Transaction Management
- Each record processed in separate transaction
- Failed records don't affect successful ones
- Checkpoint saved after successful batch
- Rollback on critical errors

## 3.8 Data Transformation

### 3.8.1 Transformation Layer
- Transform API responses to database models
- Handle nested relationships
- Map API field names to database columns
- Validate data before insertion

### 3.8.2 Transformation Functions
- One transformer function per entity type
- Handle API version differences
- Support custom field mapping
- Preserve data integrity

## 3.9 Monitoring and Logging

### 3.9.1 Extraction Logs
- Log extraction start/end times
- Track records processed per entity type
- Monitor success/failure rates
- Log performance metrics

### 3.9.2 Audit Logging
- JSON audit log in `logs/audit_log.json`
- Track all extraction operations
- Include timestamps, record counts, durations
- Support analysis and reporting

### 3.9.3 Progress Reporting
- Real-time progress updates
- Summary statistics after extraction
- Error summaries
- Performance metrics

