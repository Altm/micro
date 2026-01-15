from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum


class ProductType(str, Enum):
    SIMPLE = "simple"
    COMPOSITE = "composite"
    WINE_BOTTLE = "wine_bottle"
    OLIVE_JAR = "olive_jar"


class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    sku: str
    type: ProductType = ProductType.SIMPLE
    is_active: bool = True
    base_unit: str = "base"
    base_quantity: Decimal = Decimal("1.0")


class WineBottleSpecifics(BaseModel):
    vintage_year: Optional[int] = None
    volume_l: Optional[Decimal] = None
    alcohol_pct: Optional[Decimal] = None
    glasses_per_bottle: Optional[int] = None


class OliveJarSpecifics(BaseModel):
    weight_g: Optional[Decimal] = None
    calories_per_100g: Optional[Decimal] = None
    has_pit: Optional[bool] = None


class CompositeProductItem(BaseModel):
    product_id: int
    quantity: Decimal = Decimal("1.0")
    unit_type: str = "base"


class ProductCreate(ProductBase):
    # Specific fields for different product types
    vintage_year: Optional[int] = None
    volume_l: Optional[Decimal] = None
    alcohol_pct: Optional[Decimal] = None
    glasses_per_bottle: Optional[int] = None
    weight_g: Optional[Decimal] = None
    calories_per_100g: Optional[Decimal] = None
    has_pit: Optional[bool] = None
    # For composite products
    component_items: Optional[List[CompositeProductItem]] = []


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sku: Optional[str] = None
    type: Optional[ProductType] = None
    is_active: Optional[bool] = None
    base_unit: Optional[str] = None
    base_quantity: Optional[Decimal] = None
    # Specific fields
    vintage_year: Optional[int] = None
    volume_l: Optional[Decimal] = None
    alcohol_pct: Optional[Decimal] = None
    glasses_per_bottle: Optional[int] = None
    weight_g: Optional[Decimal] = None
    calories_per_100g: Optional[Decimal] = None
    has_pit: Optional[bool] = None
    # For composite products
    component_items: Optional[List[CompositeProductItem]] = None


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    # Specific fields
    vintage_year: Optional[int] = None
    volume_l: Optional[Decimal] = None
    alcohol_pct: Optional[Decimal] = None
    glasses_per_bottle: Optional[int] = None
    weight_g: Optional[Decimal] = None
    calories_per_100g: Optional[Decimal] = None
    has_pit: Optional[bool] = None
    # Component items for composite products
    component_items: Optional[List[CompositeProductItem]] = []

    class Config:
        from_attributes = True


class LocationBase(BaseModel):
    name: str
    code: str
    address: Optional[str] = None
    is_active: bool = True


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class LocationResponse(LocationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StockLevelBase(BaseModel):
    product_id: int
    location_id: int
    quantity: Decimal = Decimal("0.0")
    reserved_quantity: Decimal = Decimal("0.0")
    min_stock_level: Decimal = Decimal("0.0")
    max_stock_level: Decimal = Decimal("999999.0")


class StockLevelCreate(StockLevelBase):
    pass


class StockLevelUpdate(BaseModel):
    quantity: Optional[Decimal] = None
    reserved_quantity: Optional[Decimal] = None
    min_stock_level: Optional[Decimal] = None
    max_stock_level: Optional[Decimal] = None


class StockLevelResponse(StockLevelBase):
    id: int
    created_at: datetime
    updated_at: datetime
    product: Optional[ProductResponse] = None
    location: Optional[LocationResponse] = None

    class Config:
        from_attributes = True


class CatalogItem(BaseModel):
    product: ProductResponse
    stock_level: StockLevelResponse
    price_per_unit: Decimal = Decimal("0.0")  # Price in the specific location

    class Config:
        from_attributes = True


class UnitConversionBase(BaseModel):
    product_id: int
    from_unit: str
    to_unit: str
    conversion_factor: Decimal


class UnitConversionCreate(UnitConversionBase):
    pass


class UnitConversionUpdate(BaseModel):
    conversion_factor: Optional[Decimal] = None


class UnitConversionResponse(UnitConversionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True