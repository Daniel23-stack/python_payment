"""Payment service for handling money transfers."""

from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Optional
from datetime import datetime

from src.db.models import (
    Account, Transaction, TransactionEntry, TransactionType, TransactionStatus, EntryType
)
from src.core.money import Money, parse_money
from src.core.exceptions import (
    InsufficientFundsError,
    InvalidAccountError,
    InvalidAmountError,
    CurrencyMismatchError,
    DuplicateTransactionError,
    AccountSuspendedError
)
from src.core.logging import get_logger
from src.services.account_service import AccountService
from src.services.idempotency import IdempotencyService

logger = get_logger(__name__)


class PaymentService:
    """Service for payment operations."""
    
    def __init__(self, db: Session):
        """Initialize payment service."""
        self.db = db
        self.account_service = AccountService(db)
        self.idempotency_service = IdempotencyService(db)
    
    def transfer_money(
        self,
        from_account_id: int,
        to_account_id: int,
        amount: Money,
        idempotency_key: str,
        description: Optional[str] = None,
        reference_id: Optional[str] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Transaction:
        """
        Transfer money between accounts.
        
        Args:
            from_account_id: Source account ID
            to_account_id: Destination account ID
            amount: Amount to transfer
            idempotency_key: Idempotency key for duplicate prevention
            description: Optional transaction description
            reference_id: Optional external reference ID
            user_id: Optional user ID for audit
            ip_address: Optional IP address for audit
            user_agent: Optional user agent for audit
        
        Returns:
            Transaction object
        
        Raises:
            DuplicateTransactionError: If idempotency key already exists
            InsufficientFundsError: If insufficient funds
            InvalidAccountError: If account not found
            CurrencyMismatchError: If currencies don't match
        """
        # Check idempotency
        cached_response = self.idempotency_service.check_idempotency(idempotency_key)
        if cached_response:
            transaction_id = cached_response.get("transaction_id")
            if transaction_id:
                transaction = self.db.query(Transaction).filter(
                    Transaction.transaction_id == transaction_id
                ).first()
                if transaction:
                    logger.info("Duplicate transaction prevented", idempotency_key=idempotency_key[:8])
                    raise DuplicateTransactionError(f"Transaction already processed: {transaction_id}")
        
        # Validate amount
        if amount.is_zero() or not amount.is_positive():
            raise InvalidAmountError("Amount must be positive")
        
        # Validate accounts exist and are active (with pessimistic lock)
        from_account = self.account_service.get_account_for_update(from_account_id)
        to_account = self.account_service.get_account_for_update(to_account_id)
        
        # Validate currencies match
        if from_account.currency != amount.currency:
            raise CurrencyMismatchError(
                f"From account currency {from_account.currency} != amount currency {amount.currency}"
            )
        if to_account.currency != amount.currency:
            raise CurrencyMismatchError(
                f"To account currency {to_account.currency} != amount currency {amount.currency}"
            )
        
        # Check sufficient funds
        from_balance = parse_money(from_account.balance, from_account.currency)
        if from_balance < amount:
            raise InsufficientFundsError(
                f"Insufficient funds: balance={from_balance}, required={amount}"
            )
        
        # Calculate new balances
        new_from_balance = (from_balance - amount).to_decimal()
        new_to_balance = parse_money(to_account.balance, to_account.currency)
        new_to_balance = (new_to_balance + amount).to_decimal()
        
        # Create transaction record
        transaction = Transaction(
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            amount=amount.to_decimal(),
            currency=amount.currency,
            transaction_type=TransactionType.TRANSFER,
            status=TransactionStatus.PENDING,
            idempotency_key=idempotency_key,
            reference_id=reference_id,
            description=description
        )
        self.db.add(transaction)
        self.db.flush()  # Get transaction_id
        
        try:
            # Update balances
            self.account_service.update_balance(
                from_account_id,
                new_from_balance,
                old_balance=from_account.balance
            )
            self.account_service.update_balance(
                to_account_id,
                new_to_balance,
                old_balance=to_account.balance
            )
            
            # Create double-entry bookkeeping entries
            self._create_transfer_entries(transaction, from_account_id, to_account_id, amount)
            
            # Update transaction status
            transaction.status = TransactionStatus.COMPLETED
            transaction.completed_at = datetime.utcnow()
            
            # Create audit logs
            self.account_service._create_audit_log(
                account_id=from_account_id,
                action="TRANSFER_DEBIT",
                old_balance=from_account.balance,
                new_balance=new_from_balance,
                transaction_id=transaction.transaction_id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.account_service._create_audit_log(
                account_id=to_account_id,
                action="TRANSFER_CREDIT",
                old_balance=to_account.balance,
                new_balance=new_to_balance,
                transaction_id=transaction.transaction_id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Store idempotency key
            response_data = {
                "transaction_id": transaction.transaction_id,
                "status": transaction.status.value,
                "amount": str(amount.amount),
                "currency": amount.currency
            }
            self.idempotency_service.store_idempotency(
                idempotency_key,
                transaction.transaction_id,
                response_data
            )
            
            logger.info(
                "Transfer completed",
                transaction_id=transaction.transaction_id,
                from_account=from_account_id,
                to_account=to_account_id,
                amount=str(amount)
            )
            
            return transaction
            
        except Exception as e:
            # Mark transaction as failed
            transaction.status = TransactionStatus.FAILED
            logger.error(
                "Transfer failed",
                transaction_id=transaction.transaction_id,
                error=str(e)
            )
            raise
    
    def _create_transfer_entries(
        self,
        transaction: Transaction,
        from_account_id: int,
        to_account_id: int,
        amount: Money
    ) -> None:
        """Create double-entry bookkeeping entries."""
        # Debit entry (money leaving source)
        debit_entry = TransactionEntry(
            transaction_id=transaction.transaction_id,
            account_id=from_account_id,
            entry_type=EntryType.DEBIT,
            amount=amount.to_decimal(),
            currency=amount.currency
        )
        self.db.add(debit_entry)
        
        # Credit entry (money entering destination)
        credit_entry = TransactionEntry(
            transaction_id=transaction.transaction_id,
            account_id=to_account_id,
            entry_type=EntryType.CREDIT,
            amount=amount.to_decimal(),
            currency=amount.currency
        )
        self.db.add(credit_entry)
    
    def get_transaction(self, transaction_id: int) -> Optional[Transaction]:
        """Get transaction by ID."""
        return self.db.query(Transaction).filter(
            Transaction.transaction_id == transaction_id
        ).first()
    
    def get_account_transactions(
        self,
        account_id: int,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> list[Transaction]:
        """Get transaction history for an account."""
        query = self.db.query(Transaction).filter(
            (Transaction.from_account_id == account_id) |
            (Transaction.to_account_id == account_id)
        )
        
        if start_date:
            query = query.filter(Transaction.created_at >= start_date)
        if end_date:
            query = query.filter(Transaction.created_at <= end_date)
        
        return query.order_by(Transaction.created_at.desc()).limit(limit).offset(offset).all()
    
    def reverse_transaction(
        self,
        transaction_id: int,
        reason: str,
        idempotency_key: str,
        user_id: Optional[int] = None
    ) -> Transaction:
        """
        Reverse a completed transaction.
        
        Args:
            transaction_id: Transaction to reverse
            reason: Reason for reversal
            idempotency_key: Idempotency key for reversal transaction
            user_id: Optional user ID for audit
        
        Returns:
            Reversal transaction
        """
        original_transaction = self.get_transaction(transaction_id)
        if not original_transaction:
            raise InvalidAccountError(f"Transaction {transaction_id} not found")
        
        if original_transaction.status != TransactionStatus.COMPLETED:
            raise InvalidAmountError(f"Transaction {transaction_id} cannot be reversed")
        
        # Create reversal transaction
        reversal = self.transfer_money(
            from_account_id=original_transaction.to_account_id,
            to_account_id=original_transaction.from_account_id,
            amount=parse_money(original_transaction.amount, original_transaction.currency),
            idempotency_key=idempotency_key,
            description=f"Reversal of transaction {transaction_id}: {reason}",
            reference_id=f"REV-{transaction_id}",
            user_id=user_id
        )
        
        reversal.transaction_type = TransactionType.REVERSAL
        original_transaction.status = TransactionStatus.REVERSED
        
        logger.info("Transaction reversed", original_transaction_id=transaction_id, reversal_id=reversal.transaction_id)
        
        return reversal

