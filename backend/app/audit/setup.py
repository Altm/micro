from sqlalchemy import event
from sqlalchemy.engine import Connection
from sqlalchemy.sql import Insert, Update, Delete
from sqlalchemy.dialects.postgresql import insert
from contextvars import ContextVar
from datetime import datetime
import json
import structlog
from app.models.base import Base
from app.models.audit import AuditLog
from app.db.session import engine

# Context variable to store request information
request_id_var: ContextVar[str] = ContextVar("request_id", default=None)
user_id_var: ContextVar[int] = ContextVar("user_id", default=None)
ip_address_var: ContextVar[str] = ContextVar("ip_address", default=None)
user_agent_var: ContextVar[str] = ContextVar("user_agent", default=None)

logger = structlog.get_logger(__name__)


def setup_audit_listeners():
    """Setup audit listeners for all models that inherit from Base"""
    # Get all classes that inherit from Base
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if hasattr(cls, '__tablename__') and cls.__tablename__ != 'audit_logs':
            # Attach listeners for INSERT, UPDATE, DELETE
            event.listen(cls, 'after_insert', create_after_insert_listener(cls))
            event.listen(cls, 'after_update', create_after_update_listener(cls))
            event.listen(cls, 'after_delete', create_after_delete_listener(cls))


def create_after_insert_listener(model_class):
    """Create listener for INSERT operations"""
    def after_insert(mapper, connection, target):
        # Get context variables
        request_id = request_id_var.get()
        user_id = user_id_var.get()
        ip_address = ip_address_var.get()
        user_agent = user_agent_var.get()
        
        # Prepare data for audit log
        new_data = {}
        for column in mapper.columns:
            value = getattr(target, column.name)
            if value is not None:
                new_data[column.name] = str(value) if isinstance(value, (datetime,)) else value
        
        # Create audit log entry
        audit_entry = {
            'table_name': target.__tablename__,
            'record_id': getattr(target, 'id', None),
            'operation': 'INSERT',
            'old_data': None,
            'new_data': new_data,
            'user_id': user_id,
            'request_id': request_id,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Insert audit log using a separate connection to avoid transaction conflicts
        try:
            with engine.connect() as audit_conn:
                with audit_conn.begin() as audit_trans:
                    stmt = insert(AuditLog.__table__).values(**audit_entry)
                    audit_conn.execute(stmt)
        except Exception as e:
            logger.error("Failed to create audit log for INSERT", 
                        table=target.__tablename__, 
                        record_id=getattr(target, 'id', None), 
                        error=str(e))
    
    return after_insert


def create_after_update_listener(model_class):
    """Create listener for UPDATE operations"""
    def after_update(mapper, connection, target):
        # Get context variables
        request_id = request_id_var.get()
        user_id = user_id_var.get()
        ip_address = ip_address_var.get()
        user_agent = user_agent_var.get()
        
        # Get the history of changes
        old_data = {}
        new_data = {}
        
        for attr in mapper.column_attrs:
            hist = getattr(target, f'_{attr.key}_history')
            if hist.has_changes():
                # Get the old and new values
                old_value = hist.deleted[0] if hist.deleted else getattr(target, attr.key)
                new_value = hist.added[0] if hist.added else getattr(target, attr.key)
                
                # Store in dictionaries
                if old_value is not None:
                    old_val = str(old_value) if isinstance(old_value, (datetime,)) else old_value
                    old_data[attr.key] = old_val
                
                if new_value is not None:
                    new_val = str(new_value) if isinstance(new_value, (datetime,)) else new_value
                    new_data[attr.key] = new_val
        
        # Only log if there are actual changes
        if old_data or new_data:
            # Create audit log entry
            audit_entry = {
                'table_name': target.__tablename__,
                'record_id': getattr(target, 'id', None),
                'operation': 'UPDATE',
                'old_data': old_data,
                'new_data': new_data,
                'user_id': user_id,
                'request_id': request_id,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # Insert audit log using a separate connection to avoid transaction conflicts
            try:
                with engine.connect() as audit_conn:
                    with audit_conn.begin() as audit_trans:
                        stmt = insert(AuditLog.__table__).values(**audit_entry)
                        audit_conn.execute(stmt)
            except Exception as e:
                logger.error("Failed to create audit log for UPDATE", 
                            table=target.__tablename__, 
                            record_id=getattr(target, 'id', None), 
                            error=str(e))
    
    return after_update


def create_after_delete_listener(model_class):
    """Create listener for DELETE operations"""
    def after_delete(mapper, connection, target):
        # Get context variables
        request_id = request_id_var.get()
        user_id = user_id_var.get()
        ip_address = ip_address_var.get()
        user_agent = user_agent_var.get()
        
        # Prepare data for audit log
        old_data = {}
        for column in mapper.columns:
            value = getattr(target, column.name)
            if value is not None:
                old_data[column.name] = str(value) if isinstance(value, (datetime,)) else value
        
        # Create audit log entry
        audit_entry = {
            'table_name': target.__tablename__,
            'record_id': getattr(target, 'id', None),
            'operation': 'DELETE',
            'old_data': old_data,
            'new_data': None,
            'user_id': user_id,
            'request_id': request_id,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Insert audit log using a separate connection to avoid transaction conflicts
        try:
            with engine.connect() as audit_conn:
                with audit_conn.begin() as audit_trans:
                    stmt = insert(AuditLog.__table__).values(**audit_entry)
                    audit_conn.execute(stmt)
        except Exception as e:
            logger.error("Failed to create audit log for DELETE", 
                        table=target.__tablename__, 
                        record_id=getattr(target, 'id', None), 
                        error=str(e))
    
    return after_delete


def set_audit_context(request_id: str = None, user_id: int = None, 
                     ip_address: str = None, user_agent: str = None):
    """Set audit context variables"""
    if request_id:
        request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)
    if ip_address:
        ip_address_var.set(ip_address)
    if user_agent:
        user_agent_var.set(user_agent)