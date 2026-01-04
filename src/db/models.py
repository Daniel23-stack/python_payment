"""Database models for the payment system."""

from sqlalchemy import Column, BigInteger, String, DECIMAL, Enum, Text, TIMESTAMP, ForeignKey, Integer, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from src.db.database import Base


class AccountStatus(str, enum.Enum):
    """Account status enumeration."""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


class TransactionType(str, enum.Enum):
    """Transaction type enumeration."""
    TRANSFER = "TRANSFER"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    REFUND = "REFUND"
    REVERSAL = "REVERSAL"


class TransactionStatus(str, enum.Enum):
    """Transaction status enumeration."""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class EntryType(str, enum.Enum):
    """Double-entry bookkeeping entry type."""
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class Account(Base):
    """Account model."""
    
    __tablename__ = "accounts"
    
    account_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    currency = Column(String(3), nullable=False)  # ISO 4217
    balance = Column(DECIMAL(20, 2), nullable=False, default=0.00)
    status = Column(Enum(AccountStatus), nullable=False, default=AccountStatus.ACTIVE, index=True)
    version = Column(Integer, nullable=False, default=0)  # For optimistic locking
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    transactions_from = relationship("Transaction", foreign_keys="Transaction.from_account_id", back_populates="from_account")
    transactions_to = relationship("Transaction", foreign_keys="Transaction.to_account_id", back_populates="to_account")
    entries = relationship("TransactionEntry", back_populates="account")
    audit_logs = relationship("AuditLog", back_populates="account")
    
    def __repr__(self):
        return f"<Account(account_id={self.account_id}, user_id={self.user_id}, balance={self.balance}, currency={self.currency})>"


class Transaction(Base):
    """Transaction model."""
    
    __tablename__ = "transactions"
    
    transaction_id = Column(BigInteger, primary_key=True, autoincrement=True)
    from_account_id = Column(BigInteger, ForeignKey("accounts.account_id"), nullable=True)
    to_account_id = Column(BigInteger, ForeignKey("accounts.account_id"), nullable=True)
    amount = Column(DECIMAL(20, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING, index=True)
    idempotency_key = Column(String(255), nullable=False, unique=True, index=True)
    reference_id = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp(), index=True)
    completed_at = Column(TIMESTAMP, nullable=True)
    
    # Relationships
    from_account = relationship("Account", foreign_keys=[from_account_id], back_populates="transactions_from")
    to_account = relationship("Account", foreign_keys=[to_account_id], back_populates="transactions_to")
    entries = relationship("TransactionEntry", back_populates="transaction")
    audit_logs = relationship("AuditLog", back_populates="transaction")
    
    # Indexes
    __table_args__ = (
        Index('idx_from_account_created', 'from_account_id', 'created_at'),
        Index('idx_to_account_created', 'to_account_id', 'created_at'),
        Index('idx_status_created', 'status', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Transaction(transaction_id={self.transaction_id}, type={self.transaction_type}, amount={self.amount}, status={self.status})>"


class TransactionEntry(Base):
    """Double-entry bookkeeping entry model."""
    
    __tablename__ = "transaction_entries"
    
    entry_id = Column(BigInteger, primary_key=True, autoincrement=True)
    transaction_id = Column(BigInteger, ForeignKey("transactions.transaction_id"), nullable=False, index=True)
    account_id = Column(BigInteger, ForeignKey("accounts.account_id"), nullable=False, index=True)
    entry_type = Column(Enum(EntryType), nullable=False)
    amount = Column(DECIMAL(20, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    
    # Relationships
    transaction = relationship("Transaction", back_populates="entries")
    account = relationship("Account", back_populates="entries")
    
    def __repr__(self):
        return f"<TransactionEntry(entry_id={self.entry_id}, type={self.entry_type}, amount={self.amount})>"


class AuditLog(Base):
    """Audit log model for tracking all changes."""
    
    __tablename__ = "audit_logs"
    
    log_id = Column(BigInteger, primary_key=True, autoincrement=True)
    transaction_id = Column(BigInteger, ForeignKey("transactions.transaction_id"), nullable=True, index=True)
    account_id = Column(BigInteger, ForeignKey("accounts.account_id"), nullable=True, index=True)
    action = Column(String(50), nullable=False)
    old_balance = Column(DECIMAL(20, 2), nullable=True)
    new_balance = Column(DECIMAL(20, 2), nullable=True)
    user_id = Column(BigInteger, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    extra_data = Column(JSON, nullable=True)  # Renamed from 'metadata' to avoid SQLAlchemy reserved name
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp(), index=True)
    
    # Relationships
    transaction = relationship("Transaction", back_populates="audit_logs")
    account = relationship("Account", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(log_id={self.log_id}, action={self.action}, account_id={self.account_id})>"


class IdempotencyKey(Base):
    """Idempotency key storage model."""
    
    __tablename__ = "idempotency_keys"
    
    idempotency_key = Column(String(255), primary_key=True)
    transaction_id = Column(BigInteger, ForeignKey("transactions.transaction_id"), nullable=True)
    request_hash = Column(String(64), nullable=True)
    response_data = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    expires_at = Column(TIMESTAMP, nullable=False, index=True)
    
    def __repr__(self):
        return f"<IdempotencyKey(key={self.idempotency_key[:8]}..., transaction_id={self.transaction_id})>"

