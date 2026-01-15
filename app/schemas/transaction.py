from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum
from .product import ProductResponse, LocationResponse
from .user import UserResponse


class TransactionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class SaleTransactionBase(BaseModel):
    event_id: str  # Unique identifier from terminal
    product_id: int
    location_id: int
    quantity: Decimal
    unit_type: str  # Unit type ('glass', 'bottle', 'portion', etc.)
    converted_quantity: Decimal  # Quantity in base units for stock deduction
    price_per_unit: Decimal
    total_amount: Decimal
    terminal_timestamp: Optional[datetime] = None
    user_id: Optional[int] = None


class SaleTransactionCreate(SaleTransactionBase):
    pass


class SaleTransactionUpdate(BaseModel):
    status: Optional[TransactionStatus] = None
    processed_at: Optional[datetime] = None


class SaleTransactionResponse(SaleTransactionBase):
    id: int
    status: TransactionStatus
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    product: Optional[ProductResponse] = None
    location: Optional[LocationResponse] = None
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True


class ReconciliationRequest(BaseModel):
    terminal_id: str
    start_time: datetime
    end_time: datetime
    transactions: List[SaleTransactionCreate]


class ReconciliationResult(BaseModel):
    reconciliation_id: int
    processed_count: int
    success_count: int
    failed_count: int
    status: str
    notes: Optional[str] = None


class TerminalBase(BaseModel):
    name: str
    code: str
    location_id: Optional[int] = None
    is_active: bool = True


class TerminalCreate(TerminalBase):
    pass


class TerminalUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    location_id: Optional[int] = None
    is_active: Optional[bool] = None


class TerminalResponse(TerminalBase):
    id: int
    created_at: datetime
    updated_at: datetime
    last_heartbeat: Optional[datetime] = None
    location: Optional[LocationResponse] = None

    class Config:
        from_attributes = True


class RequestLogBase(BaseModel):
    method: str
    url: str
    headers: Optional[str] = None
    body: Optional[str] = None
    response_status: Optional[int] = None
    user_id: Optional[int] = None
    terminal_id: Optional[int] = None
    processing_time_ms: Optional[int] = None
    remote_addr: Optional[str] = None


class RequestLogCreate(RequestLogBase):
    pass


class RequestLogResponse(RequestLogBase):
    id: int
    created_at: datetime
    updated_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True