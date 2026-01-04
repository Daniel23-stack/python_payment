"""Error handlers for API."""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.core.exceptions import (
    PaymentSystemException,
    InsufficientFundsError,
    InvalidAccountError,
    InvalidAmountError,
    AccountSuspendedError,
    TransactionLimitExceededError,
    DuplicateTransactionError,
    CurrencyMismatchError,
    RateLimitExceededError,
    AuthenticationError,
    PermissionDeniedError
)
from src.core.logging import get_logger

logger = get_logger(__name__)


def register_error_handlers(app):
    """Register error handlers with FastAPI app."""
    
    @app.exception_handler(PaymentSystemException)
    async def payment_system_exception_handler(request: Request, exc: PaymentSystemException):
        """Handle payment system exceptions."""
        status_code = status.HTTP_400_BAD_REQUEST
        
        if isinstance(exc, InsufficientFundsError):
            status_code = status.HTTP_400_BAD_REQUEST
        elif isinstance(exc, InvalidAccountError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, (InvalidAmountError, CurrencyMismatchError)):
            status_code = status.HTTP_400_BAD_REQUEST
        elif isinstance(exc, AccountSuspendedError):
            status_code = status.HTTP_403_FORBIDDEN
        elif isinstance(exc, DuplicateTransactionError):
            status_code = status.HTTP_409_CONFLICT
        elif isinstance(exc, RateLimitExceededError):
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
        elif isinstance(exc, AuthenticationError):
            status_code = status.HTTP_401_UNAUTHORIZED
        elif isinstance(exc, PermissionDeniedError):
            status_code = status.HTTP_403_FORBIDDEN
        
        logger.warning(
            "Payment system exception",
            error_type=type(exc).__name__,
            error_message=str(exc),
            path=request.url.path
        )
        
        return JSONResponse(
            status_code=status_code,
            content={
                "error": type(exc).__name__,
                "message": str(exc),
                "path": request.url.path
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors."""
        logger.warning(
            "Validation error",
            errors=exc.errors(),
            path=request.url.path
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "ValidationError",
                "message": "Request validation failed",
                "details": exc.errors(),
                "path": request.url.path
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(
            "Unexpected error",
            error_type=type(exc).__name__,
            error_message=str(exc),
            path=request.url.path,
            exc_info=True
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "path": request.url.path
            }
        )

