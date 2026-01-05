"""Account endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict
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
    """Request model for creating a new account."""
    currency: str = Field(
        ..., 
        min_length=3, 
        max_length=3, 
        description="ISO 4217 currency code (e.g., USD, EUR, GBP)",
        examples=["USD"]
    )
    initial_balance: Optional[str] = Field(
        None, 
        description="Initial balance as decimal string. Use string to avoid floating-point errors.",
        examples=["1000.00"]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "currency": "USD",
                "initial_balance": "500.00"
            }
        }
    )


class AccountResponse(BaseModel):
    """Response model for account details."""
    account_id: int = Field(..., description="Unique account identifier")
    user_id: int = Field(..., description="Owner's user ID")
    currency: str = Field(..., description="Account currency (ISO 4217)")
    balance: str = Field(..., description="Current balance as decimal string")
    status: str = Field(..., description="Account status (ACTIVE, SUSPENDED, CLOSED)")
    created_at: str = Field(..., description="Account creation timestamp (ISO 8601)")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "account_id": 1001,
                "user_id": 42,
                "currency": "USD",
                "balance": "1500.75",
                "status": "ACTIVE",
                "created_at": "2024-01-10T08:00:00Z"
            }
        }
    )


class BalanceResponse(BaseModel):
    """Response model for account balance inquiry."""
    account_id: int = Field(..., description="Account identifier")
    balance: str = Field(..., description="Current balance as decimal string")
    currency: str = Field(..., description="Balance currency")
    last_updated: str = Field(..., description="Last balance update timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "account_id": 1001,
                "balance": "1500.75",
                "currency": "USD",
                "last_updated": "2024-01-15T14:30:00Z"
            }
        }
    )


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str = Field(..., description="Error message")


@router.post(
    "", 
    response_model=AccountResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Create Account",
    description="""
Create a new account for the authenticated user.

## Features
- Supports multiple currencies per user
- Optional initial balance deposit
- Account is immediately active

## Supported Currencies
- USD, EUR, GBP, JPY, and more (ISO 4217 codes)
    """,
    responses={
        201: {"description": "Account created successfully", "model": AccountResponse},
        400: {"description": "Invalid request data", "model": ErrorResponse}
    }
)
async def create_account(
    request: AccountCreateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Create a new financial account.
    
    The account will be created with ACTIVE status and can immediately
    receive deposits or be used for transfers.
    """
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


@router.get(
    "/{account_id}", 
    response_model=AccountResponse,
    summary="Get Account Details",
    description="Retrieve detailed information about a specific account.",
    responses={
        200: {"description": "Account details retrieved", "model": AccountResponse},
        403: {"description": "Access denied - not account owner", "model": ErrorResponse},
        404: {"description": "Account not found", "model": ErrorResponse}
    }
)
async def get_account(
    account_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Get account details by ID.
    
    Only the account owner can view account details.
    """
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


@router.get(
    "/{account_id}/balance", 
    response_model=BalanceResponse,
    summary="Get Account Balance",
    description="""
Get the current balance of an account.

This is a lightweight endpoint optimized for frequent balance checks.
For full account details, use the GET /accounts/{account_id} endpoint.
    """,
    responses={
        200: {"description": "Balance retrieved successfully", "model": BalanceResponse},
        403: {"description": "Access denied", "model": ErrorResponse},
        404: {"description": "Account not found", "model": ErrorResponse}
    }
)
async def get_balance(
    account_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Get current account balance.
    
    Returns the real-time balance with precision to 2 decimal places.
    """
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


@router.get(
    "", 
    response_model=List[AccountResponse],
    summary="List User Accounts",
    description="""
List all accounts belonging to the authenticated user.

## Filtering
- **currency**: Filter by currency code (e.g., USD, EUR)

## Response
Returns an array of account objects, empty if no accounts exist.
    """,
    responses={
        200: {
            "description": "List of accounts",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "account_id": 1001,
                            "user_id": 42,
                            "currency": "USD",
                            "balance": "1500.75",
                            "status": "ACTIVE",
                            "created_at": "2024-01-10T08:00:00Z"
                        },
                        {
                            "account_id": 1002,
                            "user_id": 42,
                            "currency": "EUR",
                            "balance": "750.00",
                            "status": "ACTIVE",
                            "created_at": "2024-01-12T10:00:00Z"
                        }
                    ]
                }
            }
        }
    }
)
async def list_accounts(
    currency: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    List all accounts for the authenticated user.
    
    Optionally filter by currency.
    """
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

