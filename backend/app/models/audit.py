from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from app.models.base import Base, TimestampMixin
from datetime import datetime


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(100), nullable=False)  # Name of the table being audited
    record_id = Column(Integer, nullable=False)       # ID of the record being audited
    operation = Column(String(10), nullable=False)    # INSERT, UPDATE, DELETE
    old_data = Column(JSON)                           # Old values (for UPDATE/DELETE)
    new_data = Column(JSON)                           # New values (for INSERT/UPDATE)
    user_id = Column(Integer)                         # ID of user who made the change (if applicable)
    request_id = Column(String(100))                  # ID of the request that caused the change
    ip_address = Column(String(45))                   # IP address of the client
    user_agent = Column(String(500))                  # User agent string
    commit_hash = Column(String(64))                  # Git commit hash at time of change (optional)
    
    # Relationships could be added here if needed


class SystemEventLog(Base, TimestampMixin):
    __tablename__ = "system_event_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), nullable=False)  # Type of system event (e.g., 'startup', 'shutdown', 'error')
    severity = Column(String(20), default='INFO')     # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message = Column(Text)                            # Description of the event
    details = Column(JSON)                            # Additional structured data about the event
    source_module = Column(String(100))               # Module/class that generated the event
    user_id = Column(Integer)                         # ID of user related to the event (if applicable)
    request_id = Column(String(100))                  # ID of the request related to the event
    duration_ms = Column(Integer)                     # Duration of the operation (if applicable)