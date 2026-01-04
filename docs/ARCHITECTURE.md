# Payment System Architecture

## Overview

The Payment System is designed with zero tolerance for errors when handling money. It follows industry best practices for financial systems.

## Key Design Principles

1. **Never use floats for money** - Always use Decimal types
2. **ACID transactions** - Guaranteed consistency
3. **Idempotency** - Safe retries and duplicate prevention
4. **Strong consistency** - CP in CAP theorem (Consistency > Availability)
5. **Comprehensive audit trail** - Every transaction logged

## Architecture Diagram

```
┌─────────────┐
│   Clients   │
│  (Web/Mobile│
│   Apps)     │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────────────────────────────┐
│        API Gateway                  │
│  - Rate Limiting                    │
│  - Authentication                   │
│  - Request Routing                  │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│     Payment Service                 │
│  - Validation                       │
│  - Business Logic                   │
│  - Transaction Management           │
└──────┬──────────────────────────────┘
       │
       ├─────────────────┐
       ▼                 ▼
┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │    Redis     │
│  (Primary)   │  │   (Cache)    │
│              │  │              │
│ - Accounts   │  │ - Balance    │
│ - Transactions│ │   Cache      │
│ - Audit Logs │  │ - Idempotency│
└──────────────┘  └──────────────┘
```

## Components

### API Layer (`src/api/`)

- **Endpoints**: RESTful API endpoints
- **Middleware**: Rate limiting, logging, CORS
- **Error Handlers**: Centralized error handling
- **Dependencies**: Authentication, database sessions

### Service Layer (`src/services/`)

- **PaymentService**: Core payment operations
- **AccountService**: Account management
- **IdempotencyService**: Duplicate prevention
- **CacheService**: Redis caching

### Database Layer (`src/db/`)

- **Models**: SQLAlchemy ORM models
- **Database**: Session management and transactions
- **Migrations**: Alembic database migrations

### Core (`src/core/`)

- **Money**: Decimal-based money handling
- **Config**: Application configuration
- **Exceptions**: Custom exceptions
- **Logging**: Structured logging

## Data Flow

### Transfer Money Flow

1. **Request Validation**
   - Validate account IDs exist
   - Verify amount > 0
   - Validate currency
   - Check idempotency key format

2. **Idempotency Check** (Redis)
   - If key exists → return cached response
   - Set key with TTL (24 hours)

3. **Begin Database Transaction**
   - Lock accounts (SELECT FOR UPDATE)
   - Check balances
   - Verify account status

4. **Execute Transfer**
   - Debit source account
   - Credit destination account
   - Create transaction record
   - Create double-entry entries
   - Create audit log entries

5. **Commit Transaction**
   - If success → update cache, return success
   - If failure → rollback, return error

6. **Post-Processing** (Async)
   - Send notifications
   - Update analytics
   - Fraud detection checks

## Database Schema

### Accounts Table
- `account_id` (PK)
- `user_id`
- `currency` (ISO 4217)
- `balance` (DECIMAL(20,2))
- `status` (ACTIVE/SUSPENDED/CLOSED)
- `version` (for optimistic locking)

### Transactions Table
- `transaction_id` (PK)
- `from_account_id` (FK)
- `to_account_id` (FK)
- `amount` (DECIMAL(20,2))
- `currency`
- `transaction_type`
- `status`
- `idempotency_key` (UNIQUE)
- `created_at`, `completed_at`

### Transaction Entries Table (Double-Entry)
- `entry_id` (PK)
- `transaction_id` (FK)
- `account_id` (FK)
- `entry_type` (DEBIT/CREDIT)
- `amount` (DECIMAL(20,2))

### Audit Logs Table
- `log_id` (PK)
- `transaction_id` (FK)
- `account_id` (FK)
- `action`
- `old_balance`, `new_balance`
- `user_id`, `ip_address`, `user_agent`
- `created_at`

## Security

- **Authentication**: JWT tokens (Bearer authentication)
- **Authorization**: Role-based access control (RBAC)
- **Encryption**: TLS 1.3 for transit, AES-256 for rest
- **Rate Limiting**: Token bucket algorithm
- **Input Validation**: Pydantic models

## Monitoring

- **Metrics**: Prometheus metrics endpoint (`/metrics`)
- **Logging**: Structured JSON logging
- **Health Checks**: `/health` endpoint
- **Tracing**: Request correlation IDs

## Scalability

- **Horizontal Scaling**: Stateless services
- **Database**: Connection pooling, read replicas
- **Caching**: Redis for frequently accessed data
- **Sharding**: Hash-based sharding by user_id

## Trade-offs

- **CP (Consistency + Partition Tolerance)**: Money accuracy > availability
- **SQL Database**: ACID transactions required
- **Pessimistic Locking**: Guaranteed consistency
- **Synchronous Core Operations**: Immediate feedback
- **Write-Through Caching**: Strong consistency

