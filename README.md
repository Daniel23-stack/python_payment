# Payment System: Zero-Error Money Handling

A production-ready payment system designed to handle money transactions with zero tolerance for errors.

## Features

- **Decimal-based money handling** - No floating-point errors
- **ACID transactions** - Guaranteed consistency
- **Idempotency** - Safe retries and duplicate prevention
- **Double-entry bookkeeping** - Self-balancing transactions
- **Comprehensive audit trail** - Complete transaction history
- **Security** - Encryption, authentication, authorization
- **Monitoring & Observability** - Full logging and metrics

## Architecture

```
┌─────────────┐
│   Clients   │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────────────────────────────┐
│        API Gateway                  │
│  - Rate Limiting                    │
│  - Authentication                   │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│     Payment Service                 │
│  - Validation                       │
│  - Business Logic                   │
└──────┬──────────────────────────────┘
       │
       ├─────────────────┐
       ▼                 ▼
┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │    Redis     │
│  (Primary)   │  │   (Cache)    │
└──────────────┘  └──────────────┘
```

## Technology Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Cache**: Redis
- **ORM**: SQLAlchemy
- **Testing**: pytest

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 6+

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the service
uvicorn src.main:app --reload
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

## Project Structure

```
.
├── src/
│   ├── api/              # API endpoints
│   ├── core/             # Core business logic
│   ├── db/               # Database models and migrations
│   ├── services/         # Service layer
│   ├── utils/            # Utilities
│   └── main.py           # Application entry point
├── tests/                # Test suite
├── alembic/              # Database migrations
├── docs/                 # Documentation
└── requirements.txt      # Python dependencies
```

## Key Design Decisions

- **CP (Consistency + Partition Tolerance)** - Money accuracy > availability
- **SQL Database** - ACID transactions required
- **Pessimistic Locking** - Guaranteed consistency for money operations
- **Decimal Storage** - No floating-point errors
- **Write-Through Caching** - Strong consistency

## License

MIT

