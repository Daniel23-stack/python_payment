"""Account service for managing accounts."""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from decimal import Decimal

from src.db.models import Account, AccountStatus, AuditLog
from src.core.money import Money, parse_money
from src.core.exceptions import InvalidAccountError, AccountSuspendedError
from src.core.logging import get_logger
from src.services.cache import cache_service

logger = get_logger(__name__)


class AccountService:
    """Service for account operations."""
    
    def __init__(self, db: Session):
        """Initialize account service."""
        self.db = db
    
    def get_account(self, account_id: int, use_cache: bool = True) -> Account:
        """
        Get account by ID.
        
        Args:
            account_id: Account ID
            use_cache: Whether to use cache
        
        Returns:
            Account object
        
        Raises:
            InvalidAccountError: If account not found
        """
        # Check cache first
        if use_cache:
            cache_key = f"account:{account_id}"
            cached = cache_service.get_json(cache_key)
            if cached:
                # Still need to get from DB for operations, but cache helps for reads
                pass
        
        account = self.db.query(Account).filter(Account.account_id == account_id).first()
        if not account:
            raise InvalidAccountError(f"Account {account_id} not found")
        
        return account
    
    def get_account_for_update(self, account_id: int) -> Account:
        """
        Get account with pessimistic lock for update.
        
        Args:
            account_id: Account ID
        
        Returns:
            Account object with lock
        
        Raises:
            InvalidAccountError: If account not found
        """
        account = self.db.query(Account).filter(
            Account.account_id == account_id
        ).with_for_update().first()
        
        if not account:
            raise InvalidAccountError(f"Account {account_id} not found")
        
        if account.status != AccountStatus.ACTIVE:
            raise AccountSuspendedError(f"Account {account_id} is {account.status.value}")
        
        return account
    
    def get_user_accounts(self, user_id: int, currency: str = None) -> list[Account]:
        """
        Get all accounts for a user.
        
        Args:
            user_id: User ID
            currency: Optional currency filter
        
        Returns:
            List of accounts
        """
        query = self.db.query(Account).filter(Account.user_id == user_id)
        if currency:
            query = query.filter(Account.currency == currency.upper())
        return query.all()
    
    def create_account(
        self,
        user_id: int,
        currency: str,
        initial_balance: Money = None
    ) -> Account:
        """
        Create a new account.
        
        Args:
            user_id: User ID
            currency: ISO 4217 currency code
            initial_balance: Initial balance (default: zero)
        
        Returns:
            Created account
        """
        if initial_balance is None:
            initial_balance = parse_money("0.00", currency)
        
        account = Account(
            user_id=user_id,
            currency=currency.upper(),
            balance=initial_balance.to_decimal(),
            status=AccountStatus.ACTIVE
        )
        
        self.db.add(account)
        self.db.flush()  # Get account_id
        
        # Create audit log
        self._create_audit_log(
            account_id=account.account_id,
            action="ACCOUNT_CREATED",
            new_balance=account.balance,
            user_id=user_id
        )
        
        logger.info("Account created", account_id=account.account_id, user_id=user_id, currency=currency)
        return account
    
    def get_balance(self, account_id: int, use_cache: bool = True) -> Money:
        """
        Get account balance.
        
        Args:
            account_id: Account ID
            use_cache: Whether to use cache
        
        Returns:
            Money object with balance
        """
        cache_key = f"balance:{account_id}"
        
        if use_cache:
            cached = cache_service.get(cache_key)
            if cached:
                account = self.get_account(account_id, use_cache=False)
                return parse_money(cached, account.currency)
        
        account = self.get_account(account_id, use_cache=False)
        balance = parse_money(account.balance, account.currency)
        
        # Cache balance
        if use_cache:
            cache_service.set(cache_key, str(account.balance), ttl=300)
        
        return balance
    
    def update_balance(
        self,
        account_id: int,
        new_balance: Decimal,
        old_balance: Decimal = None
    ) -> Account:
        """
        Update account balance (with pessimistic lock).
        
        Args:
            account_id: Account ID
            new_balance: New balance
            old_balance: Old balance for audit
        
        Returns:
            Updated account
        """
        account = self.get_account_for_update(account_id)
        
        if old_balance is None:
            old_balance = account.balance
        
        account.balance = new_balance
        account.version += 1  # Increment version for optimistic locking
        
        # Invalidate cache
        cache_service.delete(f"balance:{account_id}")
        cache_service.delete(f"account:{account_id}")
        
        # Create audit log
        self._create_audit_log(
            account_id=account_id,
            action="BALANCE_UPDATED",
            old_balance=old_balance,
            new_balance=new_balance
        )
        
        logger.info(
            "Balance updated",
            account_id=account_id,
            old_balance=str(old_balance),
            new_balance=str(new_balance)
        )
        
        return account
    
    def _create_audit_log(
        self,
        account_id: int,
        action: str,
        old_balance: Decimal = None,
        new_balance: Decimal = None,
        transaction_id: int = None,
        user_id: int = None,
        ip_address: str = None,
        user_agent: str = None,
        metadata: dict = None
    ) -> AuditLog:
        """Create audit log entry."""
        audit_log = AuditLog(
            account_id=account_id,
            transaction_id=transaction_id,
            action=action,
            old_balance=old_balance,
            new_balance=new_balance,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata
        )
        self.db.add(audit_log)
        return audit_log

