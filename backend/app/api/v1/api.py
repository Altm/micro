from fastapi import APIRouter
from app.api.v1 import products, transactions, auth, users


api_router = APIRouter()

# Include all API routes
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])