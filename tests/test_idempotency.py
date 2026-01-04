"""Tests for idempotency."""

import pytest
from src.services.idempotency import IdempotencyService
from src.core.money import parse_money


class TestIdempotencyService:
    """Test IdempotencyService."""
    
    def test_idempotency_key_storage(self, db_session):
        """Test storing and retrieving idempotency key."""
        service = IdempotencyService(db_session)
        
        idempotency_key = "test-key-123"
        response_data = {"transaction_id": 1, "status": "COMPLETED"}
        
        # Store idempotency key
        service.store_idempotency(
            idempotency_key=idempotency_key,
            transaction_id=1,
            response_data=response_data
        )
        db_session.commit()
        
        # Retrieve idempotency key
        cached = service.check_idempotency(idempotency_key)
        assert cached is not None
        assert cached["transaction_id"] == 1
        assert cached["status"] == "COMPLETED"
    
    def test_idempotency_key_not_found(self, db_session):
        """Test retrieving non-existent idempotency key."""
        service = IdempotencyService(db_session)
        
        cached = service.check_idempotency("non-existent-key")
        assert cached is None
    
    def test_duplicate_transaction_prevention(self, db_session):
        """Test that duplicate transactions are prevented."""
        from src.services.payment_service import PaymentService
        from src.services.account_service import AccountService
        
        account_service = AccountService(db_session)
        payment_service = PaymentService(db_session)
        
        # Create accounts
        account1 = account_service.create_account(user_id=1, currency="USD", initial_balance=parse_money("100.00", "USD"))
        account2 = account_service.create_account(user_id=1, currency="USD", initial_balance=parse_money("0.00", "USD"))
        db_session.commit()
        
        idempotency_key = "duplicate-test-key"
        
        # First transfer
        transaction1 = payment_service.transfer_money(
            from_account_id=account1.account_id,
            to_account_id=account2.account_id,
            amount=parse_money("10.00", "USD"),
            idempotency_key=idempotency_key
        )
        db_session.commit()
        
        # Try duplicate transfer with same idempotency key
        from src.core.exceptions import DuplicateTransactionError
        with pytest.raises(DuplicateTransactionError):
            payment_service.transfer_money(
                from_account_id=account1.account_id,
                to_account_id=account2.account_id,
                amount=parse_money("10.00", "USD"),
                idempotency_key=idempotency_key
            )

