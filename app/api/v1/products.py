from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_db
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductResponse,
    LocationCreate, LocationUpdate, LocationResponse,
    StockLevelCreate, StockLevelUpdate, StockLevelResponse,
    CatalogItem
)
from app.services.product_service import ProductService
from app.security.rbac import (
    require_product_read, require_product_write, require_product_delete,
    require_stock_read, require_stock_write
)
from app.security.auth import get_current_active_user
from app.models.user import User


router = APIRouter()


@router.post("/products/", response_model=ProductResponse)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_product_write)
):
    service = ProductService(db)
    return await service.create_product(product)


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_product_read)
):
    service = ProductService(db)
    result = await service.get_product_by_id(product_id)
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_product_write)
):
    service = ProductService(db)
    result = await service.update_product(product_id, product)
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_product_delete)
):
    service = ProductService(db)
    success = await service.delete_product(product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}


@router.get("/products/", response_model=List[ProductResponse])
async def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_product_read)
):
    service = ProductService(db)
    return await service.get_products(skip=skip, limit=limit)


@router.post("/locations/", response_model=LocationResponse)
async def create_location(
    location: LocationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_stock_write)
):
    service = ProductService(db)
    return await service.create_location(location)


@router.get("/locations/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_stock_read)
):
    service = ProductService(db)
    result = await service.get_location_by_id(location_id)
    if not result:
        raise HTTPException(status_code=404, detail="Location not found")
    return result


@router.get("/locations/", response_model=List[LocationResponse])
async def get_locations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_stock_read)
):
    service = ProductService(db)
    return await service.get_locations(skip=skip, limit=limit)


@router.post("/stock/", response_model=StockLevelResponse)
async def create_stock_level(
    stock: StockLevelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_stock_write)
):
    service = ProductService(db)
    return await service.create_stock_level(stock)


@router.get("/stock/{product_id}/{location_id}", response_model=StockLevelResponse)
async def get_stock_level(
    product_id: int,
    location_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_stock_read)
):
    service = ProductService(db)
    result = await service.get_stock_level(product_id, location_id)
    if not result:
        raise HTTPException(status_code=404, detail="Stock level not found")
    return result


@router.get("/catalog/{location_id}", response_model=List[CatalogItem])
async def get_catalog(
    location_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_stock_read)
):
    """Get catalog for a specific location"""
    service = ProductService(db)
    return await service.get_catalog(location_id)