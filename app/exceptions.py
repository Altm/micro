class InsufficientStockError(Exception):
    """Raised when there's not enough stock to fulfill a request"""
    pass


class InvalidOperationError(Exception):
    """Raised when an invalid operation is attempted"""
    pass


class ValidationError(Exception):
    """Raised when validation fails"""
    pass


class ReconciliationError(Exception):
    """Raised when reconciliation fails"""
    pass


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass