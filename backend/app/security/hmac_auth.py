import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.transaction import Terminal
from app.core.config import settings
from sqlalchemy import select


async def verify_hmac_signature(
    request: Request,
    db: AsyncSession
) -> Terminal:
    """
    Verify HMAC signature from terminal requests
    Headers expected:
    - X-Terminal-ID: Terminal identifier
    - X-Timestamp: Request timestamp (ISO format)
    - X-Signature: HMAC-SHA256 signature
    """
    # Extract headers
    terminal_id = request.headers.get("X-Terminal-ID")
    timestamp_header = request.headers.get("X-Timestamp")
    signature = request.headers.get("X-Signature")
    
    if not all([terminal_id, timestamp_header, signature]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required headers for HMAC authentication"
        )
    
    # Validate timestamp (prevent replay attacks)
    try:
        timestamp = datetime.fromisoformat(timestamp_header.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid timestamp format"
        )
    
    # Check if timestamp is within allowed window
    now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.utcnow()
    time_diff = abs((now - timestamp).total_seconds())
    
    if time_diff > (settings.TERMINAL_TIME_WINDOW_MINUTES * 60):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Request timestamp is outside allowed window of {settings.TERMINAL_TIME_WINDOW_MINUTES} minutes"
        )
    
    # Get terminal from DB
    terminal = await get_terminal_by_code(db, terminal_id)
    if not terminal or not terminal.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive terminal"
        )
    
    # Get request body
    body = await request.body()
    
    # Construct message to sign
    # Format: method + url + timestamp + body
    message = f"{request.method}{request.url.path}{timestamp_header}{body.decode('utf-8')}"
    
    # Calculate expected signature
    expected_signature = calculate_hmac_signature(message, terminal.secret_key)
    
    # Compare signatures safely
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HMAC signature"
        )
    
    # Update terminal heartbeat
    terminal.last_heartbeat = datetime.utcnow()
    db.add(terminal)
    await db.commit()
    
    return terminal


async def get_terminal_by_code(db: AsyncSession, code: str) -> Optional[Terminal]:
    """Get terminal by its code"""
    result = await db.execute(select(Terminal).filter(Terminal.code == code))
    return result.scalar_one_or_none()


def calculate_hmac_signature(message: str, secret_key: str) -> str:
    """Calculate HMAC-SHA256 signature"""
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature


async def require_terminal_auth(request: Request, db: AsyncSession = Depends(get_db)):
    """Dependency to enforce terminal HMAC authentication"""
    return await verify_hmac_signature(request, db)