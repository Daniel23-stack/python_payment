"""Transfer endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
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
    """Request model for transfer."""
    from_account_id: int = Field(..., description="Source account ID")
    to_account_id: int = Field(..., description="Destination account ID")
    amount: str = Field(..., description="Amount as decimal string")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key (auto-generated if not provided)")
    description: Optional[str] = Field(None, description="Transaction description")
    reference_id: Optional[str] = Field(None, description="External reference ID")


class TransferResponse(BaseModel):
    """Response model for transfer."""
    transaction_id: int
    from_account_id: int
    to_account_id: int
    amount: str
    currency: str
    status: str
    created_at: str
    
    class Config:
        from_attributes = True


@router.post("", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
async def transfer_money(
    request: TransferRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Transfer money between accounts."""
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

