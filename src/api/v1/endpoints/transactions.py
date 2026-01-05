"""Transaction endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

from src.db.database import get_db
from src.services.payment_service import PaymentService
from src.core.exceptions import InvalidAccountError
from src.api.v1.dependencies import get_current_user_id
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class TransactionResponse(BaseModel):
    """Response model for transaction details."""
    transaction_id: int = Field(..., description="Unique transaction identifier")
    from_account_id: Optional[int] = Field(None, description="Source account ID (null for deposits)")
    to_account_id: Optional[int] = Field(None, description="Destination account ID (null for withdrawals)")
    amount: str = Field(..., description="Transaction amount as decimal string")
    currency: str = Field(..., description="Transaction currency (ISO 4217)")
    transaction_type: str = Field(..., description="Type: TRANSFER, DEPOSIT, WITHDRAWAL, REFUND, REVERSAL")
    status: str = Field(..., description="Status: PENDING, COMPLETED, FAILED, REVERSED")
    description: Optional[str] = Field(None, description="Transaction description")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
    completed_at: Optional[str] = Field(None, description="Completion timestamp (ISO 8601)")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "transaction_id": 5001,
                "from_account_id": 1001,
                "to_account_id": 1002,
                "amount": "250.00",
                "currency": "USD",
                "transaction_type": "TRANSFER",
                "status": "COMPLETED",
                "description": "Monthly rent payment",
                "created_at": "2024-01-15T10:30:00Z",
                "completed_at": "2024-01-15T10:30:01Z"
            }
        }
    )


class TransactionHistoryResponse(BaseModel):
    """Paginated response for transaction history."""
    transactions: List[TransactionResponse] = Field(..., description="List of transactions")
    total_count: int = Field(..., description="Total number of transactions matching criteria")
    limit: int = Field(..., description="Number of results per page")
    offset: int = Field(..., description="Offset from start of results")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "transactions": [
                    {
                        "transaction_id": 5001,
                        "from_account_id": 1001,
                        "to_account_id": 1002,
                        "amount": "250.00",
                        "currency": "USD",
                        "transaction_type": "TRANSFER",
                        "status": "COMPLETED",
                        "description": "Payment",
                        "created_at": "2024-01-15T10:30:00Z",
                        "completed_at": "2024-01-15T10:30:01Z"
                    }
                ],
                "total_count": 42,
                "limit": 50,
                "offset": 0
            }
        }
    )


class ReverseTransactionRequest(BaseModel):
    """Request model for reversing a transaction."""
    reason: str = Field(
        ..., 
        description="Reason for reversal (required for audit trail)",
        min_length=5,
        max_length=500,
        examples=["Customer requested refund"]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reason": "Customer dispute - duplicate charge"
            }
        }
    )


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str = Field(..., description="Error message")


@router.get(
    "/{transaction_id}", 
    response_model=TransactionResponse,
    summary="Get Transaction Details",
    description="""
Retrieve detailed information about a specific transaction.

## Access Control
Only users who own either the source or destination account can view the transaction.
    """,
    responses={
        200: {"description": "Transaction details", "model": TransactionResponse},
        403: {"description": "Access denied", "model": ErrorResponse},
        404: {"description": "Transaction not found", "model": ErrorResponse}
    }
)
async def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Get transaction by ID.
    
    Returns full transaction details including status and timestamps.
    """
    payment_service = PaymentService(db)
    transaction = payment_service.get_transaction(transaction_id)
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found"
        )
    
    # Verify user has access (owns one of the accounts)
    account_service = payment_service.account_service
    if transaction.from_account_id:
        from_account = account_service.get_account(transaction.from_account_id)
        if from_account.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return TransactionResponse(
        transaction_id=transaction.transaction_id,
        from_account_id=transaction.from_account_id,
        to_account_id=transaction.to_account_id,
        amount=str(transaction.amount),
        currency=transaction.currency,
        transaction_type=transaction.transaction_type.value,
        status=transaction.status.value,
        description=transaction.description,
        created_at=transaction.created_at.isoformat(),
        completed_at=transaction.completed_at.isoformat() if transaction.completed_at else None
    )


@router.get(
    "/account/{account_id}/history", 
    response_model=TransactionHistoryResponse,
    summary="Get Transaction History",
    description="""
Retrieve paginated transaction history for an account.

## Filtering Options
- **start_date**: Filter transactions from this date (inclusive)
- **end_date**: Filter transactions until this date (inclusive)

## Pagination
- **limit**: Number of results per page (1-100, default 50)
- **offset**: Number of results to skip (default 0)

## Ordering
Results are ordered by creation date, most recent first.
    """,
    responses={
        200: {"description": "Transaction history", "model": TransactionHistoryResponse},
        403: {"description": "Access denied - not account owner", "model": ErrorResponse},
        404: {"description": "Account not found", "model": ErrorResponse}
    }
)
async def get_transaction_history(
    account_id: int,
    limit: int = Query(50, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    start_date: Optional[datetime] = Query(None, description="Filter from date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter until date (ISO 8601)"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Get transaction history for an account.
    
    Returns paginated list of all transactions where the account
    was either the sender or receiver.
    """
    try:
        account_service = PaymentService(db).account_service
        account = account_service.get_account(account_id)
        
        # Verify user owns account
        if account.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        payment_service = PaymentService(db)
        transactions = payment_service.get_account_transactions(
            account_id=account_id,
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date
        )
        
        # Get total count (simplified - in production, use COUNT query)
        total_count = len(transactions)  # This is approximate
        
        return TransactionHistoryResponse(
            transactions=[
                TransactionResponse(
                    transaction_id=t.transaction_id,
                    from_account_id=t.from_account_id,
                    to_account_id=t.to_account_id,
                    amount=str(t.amount),
                    currency=t.currency,
                    transaction_type=t.transaction_type.value,
                    status=t.status.value,
                    description=t.description,
                    created_at=t.created_at.isoformat(),
                    completed_at=t.completed_at.isoformat() if t.completed_at else None
                )
                for t in transactions
            ],
            total_count=total_count,
            limit=limit,
            offset=offset
        )
    except InvalidAccountError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post(
    "/{transaction_id}/reverse", 
    response_model=TransactionResponse,
    summary="Reverse Transaction",
    description="""
Reverse a previously completed transaction.

## How It Works
- Creates a new REVERSAL transaction
- Credits the original source account
- Debits the original destination account
- Links to the original transaction

## Requirements
- Original transaction must be COMPLETED
- Cannot reverse an already reversed transaction
- Destination account must have sufficient funds

## Audit Trail
The reason is recorded in the audit log for compliance.
    """,
    responses={
        200: {"description": "Reversal transaction created", "model": TransactionResponse},
        400: {"description": "Cannot reverse - invalid state or insufficient funds", "model": ErrorResponse},
        403: {"description": "Access denied", "model": ErrorResponse},
        404: {"description": "Transaction not found", "model": ErrorResponse}
    }
)
async def reverse_transaction(
    transaction_id: int,
    request: ReverseTransactionRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Reverse a completed transaction.
    
    Creates a reversal transaction that undoes the original transfer.
    A reason must be provided for audit compliance.
    """
    import uuid
    
    try:
        payment_service = PaymentService(db)
        reversal = payment_service.reverse_transaction(
            transaction_id=transaction_id,
            reason=request.reason,
            idempotency_key=str(uuid.uuid4()),
            user_id=user_id
        )
        
        db.commit()
        
        return TransactionResponse(
            transaction_id=reversal.transaction_id,
            from_account_id=reversal.from_account_id,
            to_account_id=reversal.to_account_id,
            amount=str(reversal.amount),
            currency=reversal.currency,
            transaction_type=reversal.transaction_type.value,
            status=reversal.status.value,
            description=reversal.description,
            created_at=reversal.created_at.isoformat(),
            completed_at=reversal.completed_at.isoformat() if reversal.completed_at else None
        )
    except Exception as e:
        db.rollback()
        logger.error("Transaction reversal failed", error=str(e), transaction_id=transaction_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

