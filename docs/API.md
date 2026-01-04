# Payment System API Documentation

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All endpoints require authentication via Bearer token:

```
Authorization: Bearer <token>
```

## Endpoints

### Accounts

#### Create Account

```http
POST /accounts
Content-Type: application/json

{
  "currency": "USD",
  "initial_balance": "100.00"
}
```

**Response:**
```json
{
  "account_id": 1,
  "user_id": 1,
  "currency": "USD",
  "balance": "100.00",
  "status": "ACTIVE",
  "created_at": "2024-01-01T00:00:00"
}
```

#### Get Account

```http
GET /accounts/{account_id}
```

#### Get Balance

```http
GET /accounts/{account_id}/balance
```

**Response:**
```json
{
  "account_id": 1,
  "balance": "100.00",
  "currency": "USD",
  "last_updated": "2024-01-01T00:00:00"
}
```

#### List Accounts

```http
GET /accounts?currency=USD
```

### Transfers

#### Transfer Money

```http
POST /transfers
Content-Type: application/json

{
  "from_account_id": 1,
  "to_account_id": 2,
  "amount": "50.00",
  "currency": "USD",
  "idempotency_key": "unique-key-123",
  "description": "Payment for services",
  "reference_id": "REF-123"
}
```

**Response:**
```json
{
  "transaction_id": 1,
  "from_account_id": 1,
  "to_account_id": 2,
  "amount": "50.00",
  "currency": "USD",
  "status": "COMPLETED",
  "created_at": "2024-01-01T00:00:00"
}
```

### Transactions

#### Get Transaction

```http
GET /transactions/{transaction_id}
```

#### Get Transaction History

```http
GET /transactions/account/{account_id}/history?limit=50&offset=0&start_date=2024-01-01&end_date=2024-12-31
```

#### Reverse Transaction

```http
POST /transactions/{transaction_id}/reverse
Content-Type: application/json

{
  "reason": "Customer requested refund"
}
```

## Error Responses

### 400 Bad Request

```json
{
  "error": "InsufficientFundsError",
  "message": "Insufficient funds: balance=10.00, required=50.00",
  "path": "/api/v1/transfers"
}
```

### 404 Not Found

```json
{
  "error": "InvalidAccountError",
  "message": "Account 999 not found",
  "path": "/api/v1/accounts/999"
}
```

### 409 Conflict

```json
{
  "error": "DuplicateTransactionError",
  "message": "Transaction already processed: 123",
  "path": "/api/v1/transfers"
}
```

### 429 Too Many Requests

```json
{
  "error": "RateLimitExceededError",
  "message": "Rate limit exceeded",
  "path": "/api/v1/transfers"
}
```

## Idempotency

All write operations support idempotency keys. Include an `idempotency_key` in your request to prevent duplicate processing. If a request with the same key is processed twice, the second request will return the same result without creating a duplicate transaction.

## Rate Limiting

- 100 requests per minute per IP address
- 1000 requests per hour per IP address

Rate limit headers:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Time when limit resets

