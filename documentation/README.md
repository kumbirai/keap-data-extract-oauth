# Keap Data Extractor - OAuth2 Project Plan

This directory contains the complete project plan for building a production-grade Keap data extraction application using OAuth2 authentication.

## Document Structure

The project plan is organized into the following sections:

1. **[Project Overview](01-project-overview.md)** - Project purpose, objectives, scope, and structure
2. **[OAuth2 Authentication Design](02-oauth2-authentication.md)** - OAuth2 implementation details
3. **[Data Extraction Design](03-data-extraction-design.md)** - Data extraction architecture and design
4. **[Database Design](04-database-design.md)** - Database schema and design
5. **[Implementation Phases](05-implementation-phases.md)** - Phased implementation plan
6. **[Security Considerations](06-security-considerations.md)** - Security requirements and best practices
7. **[Testing Strategy](07-testing-strategy.md)** - Testing approach and requirements
8. **[Deployment Guide](08-deployment-guide.md)** - Deployment instructions and procedures
9. **[Appendix](09-appendix.md)** - Reference materials and additional information
10. **[VPS deployment (KVM 2)](vps-kvm2-deployment/README.md)** - Ubuntu + PostgreSQL + extractor; Power BI on Windows via SSH tunnel
11. **[Stripe BI (PostgreSQL extension)](stripe/README.md)** - Stripe dimensions, facts, settlement, refunds; schema, extract integration, and reporting alongside Keap tables

## Quick Start

1. Read the [Project Overview](01-project-overview.md) for a high-level understanding
2. Review [OAuth2 Authentication Design](02-oauth2-authentication.md) for authentication details
3. Check [Implementation Phases](05-implementation-phases.md) for development roadmap
4. Refer to [Deployment Guide](08-deployment-guide.md) when ready to deploy
5. For a small VPS (e.g. KVM 2) with Power BI on a Windows PC, see [VPS deployment (KVM 2)](vps-kvm2-deployment/README.md)

## Key Features

- **OAuth2 Authentication**: Secure OAuth2 implementation with automatic token refresh
- **Checkpoint System**: Resumable data extraction with progress tracking
- **Incremental Updates**: Extract only changed data since last run
- **Production Ready**: Comprehensive error handling, logging, and monitoring
- **Backward Compatible**: Maintains existing architecture patterns

## Requirements

- Python 3.8+
- PostgreSQL 12+
- Keap OAuth2 credentials (client_id, client_secret)
- Internet access for API calls

## Next Steps

1. Review all documentation sections
2. Set up development environment
3. Obtain OAuth2 credentials from Keap
4. Begin Phase 1 implementation (OAuth2 Foundation)

## Related Documentation

- [Keap REST API Documentation](https://developer.keap.com/docs/rest/)
- [Keap OAuth2 Guide](https://developer.infusionsoft.com/getting-started-oauth-keys/)

