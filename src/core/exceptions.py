"""Custom exceptions for the payment system."""


class PaymentSystemException(Exception):
    """Base exception for payment system."""
    pass


class InsufficientFundsError(PaymentSystemException):
    """Raised when account has insufficient funds."""
    pass


class InvalidAccountError(PaymentSystemException):
    """Raised when account is invalid or not found."""
    pass


class InvalidAmountError(PaymentSystemException):
    """Raised when transaction amount is invalid."""
    pass


class AccountSuspendedError(PaymentSystemException):
    """Raised when account is suspended."""
    pass


class TransactionLimitExceededError(PaymentSystemException):
    """Raised when transaction limit is exceeded."""
    pass


class DuplicateTransactionError(PaymentSystemException):
    """Raised when duplicate transaction is detected."""
    pass


class CurrencyMismatchError(PaymentSystemException):
    """Raised when currencies don't match."""
    pass


class DatabaseError(PaymentSystemException):
    """Raised when database operation fails."""
    pass


class ConcurrentModificationError(PaymentSystemException):
    """Raised when concurrent modification is detected."""
    pass


class RateLimitExceededError(PaymentSystemException):
    """Raised when rate limit is exceeded."""
    pass


class AuthenticationError(PaymentSystemException):
    """Raised when authentication fails."""
    pass


class PermissionDeniedError(PaymentSystemException):
    """Raised when user doesn't have permission."""
    pass

