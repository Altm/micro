from sqlalchemy import Column, Integer, String, Text, Boolean, Numeric, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin
from enum import Enum


# Association table for composite products
composite_product_items = Table(
    'composite_product_items',
    Base.metadata,
    Column('parent_product_id', Integer, ForeignKey('products.id'), primary_key=True),
    Column('child_product_id', Integer, ForeignKey('products.id'), primary_key=True),
    Column('quantity', Numeric(10, 4), nullable=False, default=1.0),  # How much of child is needed for parent
    Column('unit_type', String(50), nullable=False, default='base')  # 'base', 'glass', etc.
)


class ProductType(str, Enum):
    SIMPLE = "simple"
    COMPOSITE = "composite"
    WINE_BOTTLE = "wine_bottle"
    OLIVE_JAR = "olive_jar"


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    sku = Column(String(100), unique=True, index=True)
    type = Column(String(50), default=ProductType.SIMPLE.value)
    is_active = Column(Boolean, default=True)
    
    # Common fields for all products
    base_unit = Column(String(50), default="base")  # bottle, jar, piece, etc.
    base_quantity = Column(Numeric(10, 4), default=1.0)  # How many base units this represents
    
    # Specific fields for wine bottles
    vintage_year = Column(Integer)  # Only for wine bottles
    volume_l = Column(Numeric(6, 3))  # Volume in liters
    alcohol_pct = Column(Numeric(5, 2))  # Alcohol percentage
    glasses_per_bottle = Column(Integer)  # Number of glasses per bottle
    
    # Specific fields for olive jars
    weight_g = Column(Numeric(8, 2))  # Weight in grams
    calories_per_100g = Column(Numeric(6, 2))
    has_pit = Column(Boolean, default=False)  # For olives
    
    # Relationships
    children = relationship(
        "Product",
        secondary=composite_product_items,
        primaryjoin=id == composite_product_items.c.parent_product_id,
        secondaryjoin=id == composite_product_items.c.child_product_id,
        back_populates="parents"
    )
    parents = relationship(
        "Product", 
        secondary=composite_product_items,
        primaryjoin=id == composite_product_items.c.child_product_id,
        secondaryjoin=id == composite_product_items.c.parent_product_id,
        back_populates="children"
    )
    
    # Stock relationships
    stock_levels = relationship("StockLevel", back_populates="product")
    sales = relationship("SaleTransaction", back_populates="product")


class Location(Base, TimestampMixin):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, index=True)  # e.g., 'bar_1', 'restaurant_main'
    address = Column(Text)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    stock_levels = relationship("StockLevel", back_populates="location")
    users = relationship("User", back_populates="location")


class StockLevel(Base, TimestampMixin):
    __tablename__ = "stock_levels"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    quantity = Column(Numeric(12, 4), default=0.0)  # Current stock level in base units
    reserved_quantity = Column(Numeric(12, 4), default=0.0)  # Reserved for pending orders
    min_stock_level = Column(Numeric(12, 4), default=0.0)
    max_stock_level = Column(Numeric(12, 4), default=999999.0)
    
    # Relationships
    product = relationship("Product", back_populates="stock_levels")
    location = relationship("Location", back_populates="stock_levels")


class UnitConversion(Base, TimestampMixin):
    __tablename__ = "unit_conversions"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    from_unit = Column(String(50), nullable=False)  # e.g., 'bottle'
    to_unit = Column(String(50), nullable=False)    # e.g., 'glass'
    conversion_factor = Column(Numeric(10, 6), nullable=False)  # How many 'to' units in 1 'from' unit
    
    # Relationships
    product = relationship("Product")