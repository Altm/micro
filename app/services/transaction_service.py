from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from app.models.transaction import SaleTransaction, ReconciliationLog, Terminal, TransactionStatus
from app.models.product import Product
from app.schemas.transaction import (
    SaleTransactionCreate, SaleTransactionUpdate, SaleTransactionResponse,
    ReconciliationRequest, ReconciliationResult, TerminalCreate, TerminalResponse
)
from app.services.product_service import ProductService
from app.exceptions import InsufficientStockError, ReconciliationError
from app.audit.setup import set_audit_context


class TransactionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.product_service = ProductService(db)

    async def create_sale_transaction(
        self, 
        transaction_data: SaleTransactionCreate,
        user_id: Optional[int] = None
    ) -> SaleTransactionResponse:
        """Create a new sale transaction (initially as pending)"""
        # Check if transaction with this event_id already exists (idempotency)
        stmt = select(SaleTransaction).where(
            SaleTransaction.event_id == transaction_data.event_id
        )
        result = await self.db.execute(stmt)
        existing_transaction = result.scalar_one_or_none()
        
        if existing_transaction:
            # Return existing transaction if it already exists (idempotent operation)
            return SaleTransactionResponse.from_orm(existing_transaction)
        
        # Validate product and location exist
        product = await self.db.get(Product, transaction_data.product_id)
        if not product:
            raise ValueError(f"Product with id {transaction_data.product_id} does not exist")
        
        # Create new transaction
        transaction = SaleTransaction(
            event_id=transaction_data.event_id,
            product_id=transaction_data.product_id,
            location_id=transaction_data.location_id,
            quantity=transaction_data.quantity,
            unit_type=transaction_data.unit_type,
            converted_quantity=transaction_data.converted_quantity,
            price_per_unit=transaction_data.price_per_unit,
            total_amount=transaction_data.total_amount,
            terminal_timestamp=transaction_data.terminal_timestamp,
            user_id=transaction_data.user_id or user_id,
            status=TransactionStatus.PENDING
        )
        
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        
        return SaleTransactionResponse.from_orm(transaction)

    async def get_transaction_by_event_id(self, event_id: str) -> Optional[SaleTransactionResponse]:
        """Get transaction by event ID"""
        stmt = select(SaleTransaction).where(SaleTransaction.event_id == event_id)
        result = await self.db.execute(stmt)
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            return None
            
        return SaleTransactionResponse.from_orm(transaction)

    async def confirm_transaction(self, transaction_id: int) -> SaleTransactionResponse:
        """Confirm a pending transaction and update stock levels"""
        transaction = await self.db.get(SaleTransaction, transaction_id)
        if not transaction:
            raise ValueError(f"Transaction with id {transaction_id} does not exist")
        
        if transaction.status != TransactionStatus.PENDING:
            raise ValueError(f"Cannot confirm transaction with status {transaction.status}")
        
        # Consume stock
        try:
            await self.product_service.consume_stock(
                product_id=transaction.product_id,
                location_id=transaction.location_id,
                quantity=transaction.converted_quantity
            )
        except InsufficientStockError as e:
            # Mark transaction as failed if insufficient stock
            transaction.status = TransactionStatus.FAILED
            transaction.processed_at = datetime.utcnow()
            self.db.add(transaction)
            await self.db.commit()
            raise e
        
        # Update transaction status
        transaction.status = TransactionStatus.CONFIRMED
        transaction.processed_at = datetime.utcnow()
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        
        return SaleTransactionResponse.from_orm(transaction)

    async def cancel_transaction(self, transaction_id: int) -> SaleTransactionResponse:
        """Cancel a pending transaction"""
        transaction = await self.db.get(SaleTransaction, transaction_id)
        if not transaction:
            raise ValueError(f"Transaction with id {transaction_id} does not exist")
        
        if transaction.status != TransactionStatus.PENDING:
            raise ValueError(f"Cannot cancel transaction with status {transaction.status}")
        
        # Release reserved stock if any
        await self.product_service.release_reserved_stock(
            product_id=transaction.product_id,
            location_id=transaction.location_id,
            quantity=transaction.converted_quantity
        )
        
        # Update transaction status
        transaction.status = TransactionStatus.CANCELLED
        transaction.processed_at = datetime.utcnow()
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        
        return SaleTransactionResponse.from_orm(transaction)

    async def reconcile_transactions(
        self,
        terminal_id: str,
        start_time: datetime,
        end_time: datetime,
        transactions: List[SaleTransactionCreate]
    ) -> ReconciliationResult:
        """Reconcile transactions from terminal"""
        # Create reconciliation log entry
        reconciliation_log = ReconciliationLog(
            start_time=start_time,
            end_time=end_time,
            terminal_id=terminal_id,
            status="running"
        )
        self.db.add(reconciliation_log)
        await self.db.flush()  # To get the ID
        
        processed_count = 0
        success_count = 0
        failed_count = 0
        
        # Process each transaction
        for transaction_data in transactions:
            processed_count += 1
            try:
                # Create or get existing transaction (idempotent)
                transaction = await self.create_sale_transaction(transaction_data)
                
                # Confirm the transaction
                if transaction.status == TransactionStatus.PENDING:
                    await self.confirm_transaction(transaction.id)
                
                success_count += 1
            except Exception as e:
                failed_count += 1
                # Log the error but continue processing other transactions
                print(f"Error processing transaction {transaction_data.event_id}: {str(e)}")
        
        # Update reconciliation log
        reconciliation_log.processed_count = processed_count
        reconciliation_log.success_count = success_count
        reconciliation_log.failed_count = failed_count
        reconciliation_log.status = "completed"
        reconciliation_log.notes = f"Processed {processed_count} transactions: {success_count} succeeded, {failed_count} failed"
        
        self.db.add(reconciliation_log)
        await self.db.commit()
        await self.db.refresh(reconciliation_log)
        
        return ReconciliationResult(
            reconciliation_id=reconciliation_log.id,
            processed_count=processed_count,
            success_count=success_count,
            failed_count=failed_count,
            status=reconciliation_log.status,
            notes=reconciliation_log.notes
        )

    async def get_pending_transactions(self, location_id: Optional[int] = None) -> List[SaleTransactionResponse]:
        """Get all pending transactions"""
        stmt = select(SaleTransaction).where(
            SaleTransaction.status == TransactionStatus.PENDING
        )
        
        if location_id:
            stmt = stmt.where(SaleTransaction.location_id == location_id)
        
        result = await self.db.execute(stmt)
        transactions = result.scalars().all()
        
        return [SaleTransactionResponse.from_orm(t) for t in transactions]

    async def create_terminal(self, terminal_data: TerminalCreate) -> TerminalResponse:
        """Create a new terminal"""
        # Generate a secure secret key for the terminal
        import secrets
        secret_key = secrets.token_hex(32)  # 64 character hex string
        
        terminal = Terminal(
            name=terminal_data.name,
            code=terminal_data.code,
            location_id=terminal_data.location_id,
            is_active=terminal_data.is_active,
            secret_key=secret_key
        )
        
        self.db.add(terminal)
        await self.db.commit()
        await self.db.refresh(terminal)
        
        # Don't include the secret key in the response
        terminal_response = TerminalResponse(
            id=terminal.id,
            name=terminal.name,
            code=terminal.code,
            location_id=terminal.location_id,
            is_active=terminal.is_active,
            created_at=terminal.created_at,
            updated_at=terminal.updated_at,
            last_heartbeat=terminal.last_heartbeat,
            location=terminal.location
        )
        
        return terminal_response

    async def get_terminal_by_code(self, code: str) -> Optional[TerminalResponse]:
        """Get terminal by code"""
        stmt = select(Terminal).where(Terminal.code == code)
        result = await self.db.execute(stmt)
        terminal = result.scalar_one_or_none()
        
        if not terminal:
            return None
            
        return TerminalResponse(
            id=terminal.id,
            name=terminal.name,
            code=terminal.code,
            location_id=terminal.location_id,
            is_active=terminal.is_active,
            created_at=terminal.created_at,
            updated_at=terminal.updated_at,
            last_heartbeat=terminal.last_heartbeat,
            location=terminal.location
        )