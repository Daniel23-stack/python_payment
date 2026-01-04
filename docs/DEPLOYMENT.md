# Deployment Guide

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Docker (optional)

## Local Development Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd payment-system
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 5. Setup Database

```bash
# Create database
createdb payment_system

# Run migrations
alembic upgrade head
```

### 6. Start Redis

```bash
redis-server
```

### 7. Run Application

```bash
uvicorn src.main:app --reload
```

## Docker Deployment

### Build Image

```bash
docker build -t payment-system .
```

### Run Container

```bash
docker-compose up -d
```

## Production Deployment

### Environment Variables

Set the following environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_HOST`: Redis host
- `SECRET_KEY`: Secret key for JWT tokens
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)

### Database Migrations

```bash
alembic upgrade head
```

### Run with Gunicorn

```bash
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Health Checks

- Health endpoint: `GET /health`
- Metrics endpoint: `GET /metrics`

## Monitoring

- Prometheus metrics available at `/metrics`
- Structured logs in JSON format
- Health checks for database and cache

## Backup Strategy

1. **Database Backups**: Daily automated backups
2. **Point-in-Time Recovery**: Enabled
3. **Backup Retention**: 7 days

## Disaster Recovery

- **RTO**: < 1 hour
- **RPO**: < 5 minutes
- **Multi-Region**: Configured for high availability

