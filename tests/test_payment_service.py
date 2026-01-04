"""Tests for payment service."""

import pytest
from decimal import Decimal

from src.services.payment_service import PaymentService
from src.services.account_service import AccountService
from src.core.money import parse_money
from src.core.exceptions import (
    InsufficientFundsError,
    InvalidAccountError,
    InvalidAmountError,
    CurrencyMismatchError
)
from src.db.models import AccountStatus


class TestPaymentService:
    """Test PaymentService."""
    
    def test_transfer_money_success(self, db_session):
        """Test successful money transfer."""
        account_service = AccountService(db_session)
        payment_service = PaymentService(db_session)
        
        # Create accounts
        account1 = account_service.create_account(user_id=1, currency="USD", initial_balance=parse_money("100.00", "USD"))
        account2 = account_service.create_account(user_id=1, currency="USD", initial_balance=parse_money("50.00", "USD"))
        db_session.commit()
        
        # Transfer money
        transaction = payment_service.transfer_money(
            from_account_id=account1.account_id,
            to_account_id=account2.account_id,
            amount=parse_money("30.00", "USD"),
            idempotency_key="test-key-1"
        )
        db_session.commit()
        
        # Verify balances
        account1 = account_service.get_account(account1.account_id)
        account2 = account_service.get_account(account2.account_id)
        
        assert account1.balance == Decimal("70.00")
        assert account2.balance == Decimal("80.00")
        assert transaction.status.value == "COMPLETED"
    
    def test_transfer_insufficient_funds(self, db_session):
        """Test transfer with insufficient funds."""
        account_service = AccountService(db_session)
        payment_service = PaymentService(db_session)
        
        # Create accounts
        account1 = account_service.create_account(user_id=1, currency="USD", initial_balance=parse_money("10.00", "USD"))
        account2 = account_service.create_account(user_id=1, currency="USD", initial_balance=parse_money("0.00", "USD"))
        db_session.commit()
        
        # Try to transfer more than available
        with pytest.raises(InsufficientFundsError):
            payment_service.transfer_money(
                from_account_id=account1.account_id,
                to_account_id=account2.account_id,
                amount=parse_money("50.00", "USD"),
                idempotency_key="test-key-2"
            )
    
    def test_transfer_invalid_account(self, db_session):
        """Test transfer with invalid account."""
        account_service = AccountService(db_session)
        payment_service = PaymentService(db_session)
        
        account1 = account_service.create_account(user_id=1, currency="USD", initial_balance=parse_money("100.00", "USD"))
        db_session.commit()
        
        # Try to transfer to non-existent account
        with pytest.raises(InvalidAccountError):
            payment_service.transfer_money(
                from_account_id=account1.account_id,
                to_account_id=99999,
                amount=parse_money("10.00", "USD"),
                idempotency_key="test-key-3"
            )
    
    def test_transfer_currency_mismatch(self, db_session):
        """Test transfer with currency mismatch."""
        account_service = AccountService(db_session)
        payment_service = PaymentService(db_session)
        
        account1 = account_service.create_account(user_id=1, currency="USD", initial_balance=parse_money("100.00", "USD"))
        account2 = account_service.create_account(user_id=1, currency="EUR", initial_balance=parse_money("50.00", "EUR"))
        db_session.commit()
        
        # Try to transfer USD to EUR account
        with pytest.raises(CurrencyMismatchError):
            payment_service.transfer_money(
                from_account_id=account1.account_id,
                to_account_id=account2.account_id,
                amount=parse_money("10.00", "USD"),
                idempotency_key="test-key-4"
            )
    
    def test_transfer_zero_amount(self, db_session):
        """Test transfer with zero amount."""
        account_service = AccountService(db_session)
        payment_service = PaymentService(db_session)
        
        account1 = account_service.create_account(user_id=1, currency="USD", initial_balance=parse_money("100.00", "USD"))
        account2 = account_service.create_account(user_id=1, currency="USD", initial_balance=parse_money("50.00", "USD"))
        db_session.commit()
        
        # Try to transfer zero amount
        with pytest.raises(InvalidAmountError):
            payment_service.transfer_money(
                from_account_id=account1.account_id,
                to_account_id=account2.account_id,
                amount=parse_money("0.00", "USD"),
                idempotency_key="test-key-5"
            )

