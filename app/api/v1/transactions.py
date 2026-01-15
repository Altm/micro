from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_db
from app.schemas.transaction import (
    SaleTransactionCreate, SaleTransactionUpdate, SaleTransactionResponse,
    ReconciliationRequest, ReconciliationResult, TerminalCreate, TerminalResponse
)
from app.services.transaction_service import TransactionService
from app.security.rbac import (
    require_stock_write, require_stock_read
)
from app.security.auth import get_current_active_user
from app.security.hmac_auth import require_terminal_auth
from app.models.user import User
from fastapi import Request


router = APIRouter()


@router.post("/sales/", response_model=SaleTransactionResponse)
async def create_sale_transaction(
    transaction: SaleTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_stock_write)
):
    """Create a new sale transaction (human user initiated)"""
    service = TransactionService(db)
    return await service.create_sale_transaction(transaction, user_id=current_user.id)


@router.post("/terminal-sales/", response_model=SaleTransactionResponse)
async def create_terminal_sale_transaction(
    request: Request,
    transaction: SaleTransactionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new sale transaction from terminal (HMAC authenticated)"""
    # Verify terminal authentication
    terminal = await require_terminal_auth(request, db)
    
    service = TransactionService(db)
    return await service.create_sale_transaction(transaction)


@router.get("/sales/{transaction_id}", response_model=SaleTransactionResponse)
async def get_sale_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_stock_read)
):
    from app.models.transaction import SaleTransaction
    from sqlalchemy import select
    
    # Directly fetch from DB since our service doesn't have this method yet
    stmt = select(SaleTransaction).where(SaleTransaction.id == transaction_id)
    result = await db.execute(stmt)
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Manually construct response since from_orm might not work directly
    return SaleTransactionResponse(
        id=transaction.id,
        event_id=transaction.event_id,
        product_id=transaction.product_id,
        location_id=transaction.location_id,
        quantity=transaction.quantity,
        unit_type=transaction.unit_type,
        converted_quantity=transaction.converted_quantity,
        price_per_unit=transaction.price_per_unit,
        total_amount=transaction.total_amount,
        status=transaction.status,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
        processed_at=transaction.processed_at,
        terminal_timestamp=transaction.terminal_timestamp,
        user_id=transaction.user_id
    )


@router.patch("/sales/{transaction_id}/confirm", response_model=SaleTransactionResponse)
async def confirm_sale_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_stock_write)
):
    """Confirm a pending transaction and update stock levels"""
    service = TransactionService(db)
    try:
        return await service.confirm_transaction(transaction_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/sales/{transaction_id}/cancel", response_model=SaleTransactionResponse)
async def cancel_sale_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_stock_write)
):
    """Cancel a pending transaction"""
    service = TransactionService(db)
    try:
        return await service.cancel_transaction(transaction_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reconcile/", response_model=ReconciliationResult)
async def reconcile_terminal_transactions(
    request: Request,
    reconciliation_request: ReconciliationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Reconcile transactions from terminal"""
    # Verify terminal authentication
    terminal = await require_terminal_auth(request, db)
    
    service = TransactionService(db)
    return await service.reconcile_transactions(
        terminal_id=reconciliation_request.terminal_id,
        start_time=reconciliation_request.start_time,
        end_time=reconciliation_request.end_time,
        transactions=reconciliation_request.transactions
    )


@router.get("/pending-sales/", response_model=List[SaleTransactionResponse])
async def get_pending_transactions(
    location_id: int = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_stock_read)
):
    """Get all pending transactions for a location"""
    service = TransactionService(db)
    return await service.get_pending_transactions(location_id)


@router.post("/terminals/", response_model=TerminalResponse)
async def create_terminal(
    terminal: TerminalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_stock_write)  # Only authorized users can create terminals
):
    """Create a new terminal with HMAC authentication capability"""
    service = TransactionService(db)
    return await service.create_terminal(terminal)


@router.get("/terminals/{code}", response_model=TerminalResponse)
async def get_terminal(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_stock_read)
):
    """Get terminal by code"""
    service = TransactionService(db)
    result = await service.get_terminal_by_code(code)
    if not result:
        raise HTTPException(status_code=404, detail="Terminal not found")
    return result