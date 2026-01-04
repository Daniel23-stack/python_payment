"""Account endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List

from src.db.database import get_db
from src.services.account_service import AccountService
from src.core.money import Money, parse_money
from src.core.exceptions import InvalidAccountError, AccountSuspendedError
from src.api.v1.dependencies import get_current_user_id
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class AccountCreateRequest(BaseModel):
    """Request model for creating account."""
    currency: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code")
    initial_balance: Optional[str] = Field(None, description="Initial balance as decimal string")


class AccountResponse(BaseModel):
    """Response model for account."""
    account_id: int
    user_id: int
    currency: str
    balance: str
    status: str
    created_at: str
    
    class Config:
        from_attributes = True


class BalanceResponse(BaseModel):
    """Response model for balance."""
    account_id: int
    balance: str
    currency: str
    last_updated: str


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    request: AccountCreateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Create a new account."""
    try:
        initial_balance = None
        if request.initial_balance:
            initial_balance = parse_money(request.initial_balance, request.currency)
        
        account_service = AccountService(db)
        account = account_service.create_account(
            user_id=user_id,
            currency=request.currency,
            initial_balance=initial_balance
        )
        db.commit()
        
        return AccountResponse(
            account_id=account.account_id,
            user_id=account.user_id,
            currency=account.currency,
            balance=str(account.balance),
            status=account.status.value,
            created_at=account.created_at.isoformat()
        )
    except Exception as e:
        db.rollback()
        logger.error("Account creation failed", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Get account details."""
    try:
        account_service = AccountService(db)
        account = account_service.get_account(account_id)
        
        # Verify user owns account
        if account.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return AccountResponse(
            account_id=account.account_id,
            user_id=account.user_id,
            currency=account.currency,
            balance=str(account.balance),
            status=account.status.value,
            created_at=account.created_at.isoformat()
        )
    except InvalidAccountError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{account_id}/balance", response_model=BalanceResponse)
async def get_balance(
    account_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Get account balance."""
    try:
        account_service = AccountService(db)
        account = account_service.get_account(account_id)
        
        # Verify user owns account
        if account.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        balance = account_service.get_balance(account_id)
        
        return BalanceResponse(
            account_id=account.account_id,
            balance=str(balance.amount),
            currency=balance.currency,
            last_updated=account.updated_at.isoformat()
        )
    except InvalidAccountError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("", response_model=List[AccountResponse])
async def list_accounts(
    currency: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """List user's accounts."""
    account_service = AccountService(db)
    accounts = account_service.get_user_accounts(user_id, currency=currency)
    
    return [
        AccountResponse(
            account_id=account.account_id,
            user_id=account.user_id,
            currency=account.currency,
            balance=str(account.balance),
            status=account.status.value,
            created_at=account.created_at.isoformat()
        )
        for account in accounts
    ]

