from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin
from datetime import datetime
from enum import Enum


class TransactionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class SaleTransaction(Base, TimestampMixin):
    __tablename__ = "sale_transactions"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(100), unique=True, index=True, nullable=False)  # Unique identifier from terminal
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    quantity = Column(Numeric(10, 4), nullable=False)  # Quantity sold in requested unit
    unit_type = Column(String(50), nullable=False)  # Unit type ('glass', 'bottle', 'portion', etc.)
    converted_quantity = Column(Numeric(10, 4), nullable=False)  # Quantity in base units for stock deduction
    price_per_unit = Column(Numeric(10, 2), nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), default=TransactionStatus.PENDING)  # pending, confirmed, cancelled
    processed_at = Column(DateTime)  # When the transaction was processed
    terminal_timestamp = Column(DateTime)  # When terminal sent the transaction
    user_id = Column(Integer, ForeignKey("users.id"))  # Who processed the transaction
    
    # Relationships
    product = relationship("Product", back_populates="sales")
    location = relationship("Location")
    user = relationship("User")


class ReconciliationLog(Base, TimestampMixin):
    __tablename__ = "reconciliation_logs"

    id = Column(Integer, primary_key=True, index=True)
    start_time = Column(DateTime, nullable=False)  # Start of reconciliation period
    end_time = Column(DateTime, nullable=False)    # End of reconciliation period
    terminal_id = Column(String(100), nullable=False)  # Which terminal sent the data
    processed_count = Column(Integer, default=0)   # How many transactions were processed
    success_count = Column(Integer, default=0)     # How many were successful
    failed_count = Column(Integer, default=0)      # How many failed
    status = Column(String(20), default="running")  # running, completed, failed
    notes = Column(String(500))                    # Additional info about the reconciliation
    
    # Relationships
    transactions = relationship("SaleTransaction")


class Terminal(Base, TimestampMixin):
    __tablename__ = "terminals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, index=True, nullable=False)  # e.g., 'bar_1_terminal_1'
    location_id = Column(Integer, ForeignKey("locations.id"))
    is_active = Column(Boolean, default=True)
    last_heartbeat = Column(DateTime)
    
    # For HMAC authentication
    secret_key = Column(String(255), nullable=False)  # Per-terminal secret for HMAC
    
    # Relationships
    location = relationship("Location")


class RequestLog(Base, TimestampMixin):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE
    url = Column(String(500), nullable=False)
    headers = Column(String(1000))  # JSON string of headers (truncated if too long)
    body = Column(String(1000))     # JSON string of body (truncated if too long)
    response_status = Column(Integer)  # HTTP response status
    user_id = Column(Integer, ForeignKey("users.id"))  # User who made the request
    terminal_id = Column(Integer, ForeignKey("terminals.id"))  # Terminal that made the request
    processing_time_ms = Column(Integer)  # How long the request took to process
    remote_addr = Column(String(45))  # IP address of the client
    
    # Relationships
    user = relationship("User")
    terminal = relationship("Terminal")