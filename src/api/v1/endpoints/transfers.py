"""Transfer endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
import uuid

from src.db.database import get_db
from src.services.payment_service import PaymentService
from src.core.money import parse_money
from src.core.exceptions import (
    InsufficientFundsError,
    InvalidAccountError,
    InvalidAmountError,
    CurrencyMismatchError,
    DuplicateTransactionError
)
from src.api.v1.dependencies import get_current_user_id
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class TransferRequest(BaseModel):
    """Request model for money transfer between accounts."""
    from_account_id: int = Field(
        ..., 
        description="Source account ID to debit",
        examples=[1001]
    )
    to_account_id: int = Field(
        ..., 
        description="Destination account ID to credit",
        examples=[1002]
    )
    amount: str = Field(
        ..., 
        description="Amount as decimal string (no floats allowed)",
        examples=["100.50"]
    )
    currency: str = Field(
        ..., 
        min_length=3, 
        max_length=3, 
        description="ISO 4217 currency code",
        examples=["USD"]
    )
    idempotency_key: Optional[str] = Field(
        None, 
        description="Unique key for idempotent requests. If same key is reused, cached response is returned.",
        examples=["txn-abc123-unique-key"]
    )
    description: Optional[str] = Field(
        None, 
        description="Human-readable transaction description",
        examples=["Payment for invoice #12345"]
    )
    reference_id: Optional[str] = Field(
        None, 
        description="External reference ID for reconciliation",
        examples=["INV-2024-001"]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "from_account_id": 1001,
                "to_account_id": 1002,
                "amount": "250.00",
                "currency": "USD",
                "idempotency_key": "unique-transfer-key-123",
                "description": "Monthly rent payment",
                "reference_id": "RENT-JAN-2024"
            }
        }
    )


class TransferResponse(BaseModel):
    """Response model for completed transfer."""
    transaction_id: int = Field(..., description="Unique transaction identifier")
    from_account_id: int = Field(..., description="Source account ID")
    to_account_id: int = Field(..., description="Destination account ID")
    amount: str = Field(..., description="Transfer amount")
    currency: str = Field(..., description="Currency code")
    status: str = Field(..., description="Transaction status (PENDING, COMPLETED, FAILED)")
    created_at: str = Field(..., description="ISO 8601 timestamp of creation")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "transaction_id": 5001,
                "from_account_id": 1001,
                "to_account_id": 1002,
                "amount": "250.00",
                "currency": "USD",
                "status": "COMPLETED",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""
    detail: str = Field(..., description="Error description")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Insufficient funds in account 1001"
            }
        }
    )


@router.post(
    "", 
    response_model=TransferResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Transfer Money",
    description="""
Transfer money between two accounts atomically.

## Features
- **ACID compliant** - All operations are atomic
- **Idempotent** - Safe to retry with same idempotency_key
- **Double-entry** - Creates balanced debit/credit entries

## Validation
- Source account must have sufficient balance
- Both accounts must exist and be active
- Currency must match for both accounts
- Amount must be positive

## Error Codes
- `400` - Invalid request (insufficient funds, invalid amount)
- `404` - Account not found
- `409` - Duplicate transaction (idempotency key reused with different data)
    """,
    responses={
        201: {
            "description": "Transfer completed successfully",
            "model": TransferResponse
        },
        400: {
            "description": "Bad request - insufficient funds or invalid data",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "insufficient_funds": {
                            "summary": "Insufficient Funds",
                            "value": {"detail": "Insufficient funds in account 1001. Available: 50.00, Required: 250.00"}
                        },
                        "invalid_amount": {
                            "summary": "Invalid Amount",
                            "value": {"detail": "Amount must be positive"}
                        }
                    }
                }
            }
        },
        404: {
            "description": "Account not found",
            "model": ErrorResponse
        },
        409: {
            "description": "Duplicate transaction",
            "model": ErrorResponse
        }
    }
)
async def transfer_money(
    request: TransferRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Transfer money between two accounts.
    
    This endpoint performs an atomic transfer ensuring:
    - The source account is debited
    - The destination account is credited
    - Both operations succeed or both fail (ACID)
    - Audit trail is created
    """
    # Generate idempotency key if not provided
    idempotency_key = request.idempotency_key or str(uuid.uuid4())
    
    try:
        amount = parse_money(request.amount, request.currency)
        
        payment_service = PaymentService(db)
        transaction = payment_service.transfer_money(
            from_account_id=request.from_account_id,
            to_account_id=request.to_account_id,
            amount=amount,
            idempotency_key=idempotency_key,
            description=request.description,
            reference_id=request.reference_id,
            user_id=user_id,
            ip_address=http_request.client.host if http_request.client else None,
            user_agent=http_request.headers.get("user-agent")
        )
        
        db.commit()
        
        return TransferResponse(
            transaction_id=transaction.transaction_id,
            from_account_id=transaction.from_account_id,
            to_account_id=transaction.to_account_id,
            amount=str(transaction.amount),
            currency=transaction.currency,
            status=transaction.status.value,
            created_at=transaction.created_at.isoformat()
        )
    except DuplicateTransactionError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except InsufficientFundsError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except (InvalidAccountError, InvalidAmountError, CurrencyMismatchError) as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        logger.error("Transfer failed", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transfer failed"
        )

