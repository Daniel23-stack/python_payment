"""Transaction endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
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
    """Response model for transaction."""
    transaction_id: int
    from_account_id: Optional[int]
    to_account_id: Optional[int]
    amount: str
    currency: str
    transaction_type: str
    status: str
    description: Optional[str]
    created_at: str
    completed_at: Optional[str]
    
    class Config:
        from_attributes = True


class TransactionHistoryResponse(BaseModel):
    """Response model for transaction history."""
    transactions: List[TransactionResponse]
    total_count: int
    limit: int
    offset: int


class ReverseTransactionRequest(BaseModel):
    """Request model for reversing transaction."""
    reason: str


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Get transaction details."""
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


@router.get("/account/{account_id}/history", response_model=TransactionHistoryResponse)
async def get_transaction_history(
    account_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Get transaction history for an account."""
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


@router.post("/{transaction_id}/reverse", response_model=TransactionResponse)
async def reverse_transaction(
    transaction_id: int,
    request: ReverseTransactionRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Reverse a completed transaction."""
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

