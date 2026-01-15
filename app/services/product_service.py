from typing import List, Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from app.models.product import Product, Location, StockLevel, UnitConversion, composite_product_items
from app.models.transaction import SaleTransaction, TransactionStatus
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductResponse, 
    LocationCreate, LocationUpdate, LocationResponse,
    StockLevelCreate, StockLevelUpdate, StockLevelResponse,
    UnitConversionCreate, UnitConversionUpdate, UnitConversionResponse
)
from app.exceptions import InsufficientStockError, InvalidOperationError


class ProductService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_product(self, product_data: ProductCreate) -> ProductResponse:
        """Create a new product with optional component items for composite products"""
        # Create the product
        product = Product(
            name=product_data.name,
            description=product_data.description,
            sku=product_data.sku,
            type=product_data.type,
            is_active=product_data.is_active,
            base_unit=product_data.base_unit,
            base_quantity=product_data.base_quantity,
            # Wine-specific fields
            vintage_year=product_data.vintage_year,
            volume_l=product_data.volume_l,
            alcohol_pct=product_data.alcohol_pct,
            glasses_per_bottle=product_data.glasses_per_bottle,
            # Olive jar-specific fields
            weight_g=product_data.weight_g,
            calories_per_100g=product_data.calories_per_100g,
            has_pit=product_data.has_pit
        )
        
        self.db.add(product)
        await self.db.flush()  # To get the product ID
        
        # Handle component items for composite products
        if product_data.component_items:
            for item in product_data.component_items:
                # Add to association table
                stmt = composite_product_items.insert().values(
                    parent_product_id=product.id,
                    child_product_id=item.product_id,
                    quantity=item.quantity,
                    unit_type=item.unit_type
                )
                await self.db.execute(stmt)
        
        await self.db.commit()
        await self.db.refresh(product)
        
        # Fetch the complete product with component items
        return await self.get_product_by_id(product.id)

    async def get_product_by_id(self, product_id: int) -> ProductResponse:
        """Get a product by ID with its component items"""
        product = await self.db.get(Product, product_id)
        if not product:
            return None
            
        # Get component items for composite products
        component_items = []
        if product.type == "composite":
            from sqlalchemy import text
            stmt = text("""
                SELECT cp.parent_product_id, cp.child_product_id, cp.quantity, cp.unit_type
                FROM composite_product_items cp
                WHERE cp.parent_product_id = :parent_id
            """)
            result = await self.db.execute(stmt, {"parent_id": product_id})
            rows = result.fetchall()
            
            for row in rows:
                from app.schemas.product import CompositeProductItem
                component_items.append(CompositeProductItem(
                    product_id=row.child_product_id,
                    quantity=row.quantity,
                    unit_type=row.unit_type
                ))
        
        # Convert to response schema
        product_dict = {
            **product.__dict__,
            'component_items': component_items
        }
        
        # Remove SQLAlchemy internal attributes
        product_dict.pop('_sa_instance_state', None)
        
        return ProductResponse(**product_dict)

    async def update_product(self, product_id: int, product_data: ProductUpdate) -> ProductResponse:
        """Update a product"""
        product = await self.db.get(Product, product_id)
        if not product:
            return None
            
        # Update fields
        update_data = product_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(product, field):
                setattr(product, field, value)
        
        # Handle component items separately if provided
        if product_data.component_items is not None:
            # Clear existing component items
            stmt = composite_product_items.delete().where(
                composite_product_items.c.parent_product_id == product_id
            )
            await self.db.execute(stmt)
            
            # Add new component items
            for item in product_data.component_items:
                stmt = composite_product_items.insert().values(
                    parent_product_id=product_id,
                    child_product_id=item.product_id,
                    quantity=item.quantity,
                    unit_type=item.unit_type
                )
                await self.db.execute(stmt)
        
        await self.db.commit()
        await self.db.refresh(product)
        
        return await self.get_product_by_id(product_id)

    async def delete_product(self, product_id: int) -> bool:
        """Delete a product"""
        product = await self.db.get(Product, product_id)
        if not product:
            return False
            
        await self.db.delete(product)
        await self.db.commit()
        return True

    async def get_products(self, skip: int = 0, limit: int = 100) -> List[ProductResponse]:
        """Get list of products"""
        stmt = select(Product).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        products = result.scalars().all()
        
        return [await self.get_product_by_id(p.id) for p in products]

    async def create_location(self, location_data: LocationCreate) -> LocationResponse:
        """Create a new location"""
        location = Location(
            name=location_data.name,
            code=location_data.code,
            address=location_data.address,
            is_active=location_data.is_active
        )
        
        self.db.add(location)
        await self.db.commit()
        await self.db.refresh(location)
        
        return LocationResponse.from_orm(location)

    async def get_location_by_id(self, location_id: int) -> LocationResponse:
        """Get a location by ID"""
        location = await self.db.get(Location, location_id)
        if not location:
            return None
        return LocationResponse.from_orm(location)

    async def get_locations(self, skip: int = 0, limit: int = 100) -> List[LocationResponse]:
        """Get list of locations"""
        stmt = select(Location).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        locations = result.scalars().all()
        
        return [LocationResponse.from_orm(loc) for loc in locations]

    async def create_stock_level(self, stock_data: StockLevelCreate) -> StockLevelResponse:
        """Create or update stock level"""
        # Check if stock level already exists
        stmt = select(StockLevel).where(
            and_(
                StockLevel.product_id == stock_data.product_id,
                StockLevel.location_id == stock_data.location_id
            )
        )
        result = await self.db.execute(stmt)
        existing_stock = result.scalar_one_or_none()
        
        if existing_stock:
            # Update existing stock level
            stmt = update(StockLevel).where(StockLevel.id == existing_stock.id).values(
                quantity=stock_data.quantity,
                reserved_quantity=stock_data.reserved_quantity,
                min_stock_level=stock_data.min_stock_level,
                max_stock_level=stock_data.max_stock_level
            )
            await self.db.execute(stmt)
            stock = existing_stock
        else:
            # Create new stock level
            stock = StockLevel(
                product_id=stock_data.product_id,
                location_id=stock_data.location_id,
                quantity=stock_data.quantity,
                reserved_quantity=stock_data.reserved_quantity,
                min_stock_level=stock_data.min_stock_level,
                max_stock_level=stock_data.max_stock_level
            )
            self.db.add(stock)
        
        await self.db.commit()
        await self.db.refresh(stock)
        
        # Load relationships
        await self.db.refresh(stock, attribute_names=['product', 'location'])
        
        return StockLevelResponse.from_orm(stock)

    async def get_stock_level(self, product_id: int, location_id: int) -> StockLevelResponse:
        """Get stock level for a specific product at a specific location"""
        stmt = select(StockLevel).where(
            and_(
                StockLevel.product_id == product_id,
                StockLevel.location_id == location_id
            )
        )
        result = await self.db.execute(stmt)
        stock = result.scalar_one_or_none()
        
        if not stock:
            return None
            
        # Load relationships
        await self.db.refresh(stock, attribute_names=['product', 'location'])
        
        return StockLevelResponse.from_orm(stock)

    async def get_catalog(self, location_id: int) -> List[Dict[str, Any]]:
        """Get catalog for a specific location"""
        stmt = (
            select(StockLevel)
            .join(Product)
            .where(StockLevel.location_id == location_id)
            .where(Product.is_active == True)
        )
        result = await self.db.execute(stmt)
        stock_levels = result.scalars().all()
        
        catalog = []
        for stock in stock_levels:
            await self.db.refresh(stock, attribute_names=['product', 'location'])
            # TODO: Add price lookup for location-specific pricing
            catalog.append({
                'product': ProductResponse.from_orm(stock.product),
                'stock_level': StockLevelResponse.from_orm(stock),
                'price_per_unit': Decimal('0.00')  # Placeholder - would come from location-specific pricing
            })
        
        return catalog

    async def convert_units(self, product_id: int, from_unit: str, to_unit: str, quantity: Decimal) -> Decimal:
        """Convert quantity from one unit to another for a product"""
        stmt = select(UnitConversion).where(
            and_(
                UnitConversion.product_id == product_id,
                UnitConversion.from_unit == from_unit,
                UnitConversion.to_unit == to_unit
            )
        )
        result = await self.db.execute(stmt)
        conversion = result.scalar_one_or_none()
        
        if not conversion:
            # If no direct conversion found, try reverse conversion
            stmt = select(UnitConversion).where(
                and_(
                    UnitConversion.product_id == product_id,
                    UnitConversion.from_unit == to_unit,
                    UnitConversion.to_unit == from_unit
                )
            )
            result = await self.db.execute(stmt)
            reverse_conversion = result.scalar_one_or_none()
            
            if reverse_conversion:
                # Reverse the conversion factor
                converted_qty = quantity / reverse_conversion.conversion_factor
                return converted_qty
            else:
                # No conversion available
                if from_unit == to_unit:
                    return quantity
                else:
                    raise InvalidOperationError(f"No conversion available from {from_unit} to {to_unit}")
        
        converted_qty = quantity * conversion.conversion_factor
        return converted_qty

    async def reserve_stock(self, product_id: int, location_id: int, quantity: Decimal) -> bool:
        """Reserve stock for pending transactions"""
        stock_level = await self.get_stock_level(product_id, location_id)
        if not stock_level:
            raise InsufficientStockError("Stock level not found")
        
        available = stock_level.quantity - stock_level.reserved_quantity
        if available < quantity:
            raise InsufficientStockError(f"Insufficient stock: requested {quantity}, available {available}")
        
        # Update reserved quantity
        stmt = update(StockLevel).where(
            and_(
                StockLevel.product_id == product_id,
                StockLevel.location_id == location_id
            )
        ).values(
            reserved_quantity=stock_level.reserved_quantity + quantity
        )
        await self.db.execute(stmt)
        await self.db.commit()
        
        return True

    async def release_reserved_stock(self, product_id: int, location_id: int, quantity: Decimal) -> bool:
        """Release reserved stock"""
        stock_level = await self.get_stock_level(product_id, location_id)
        if not stock_level:
            return False
        
        new_reserved = max(0, stock_level.reserved_quantity - quantity)
        stmt = update(StockLevel).where(
            and_(
                StockLevel.product_id == product_id,
                StockLevel.location_id == location_id
            )
        ).values(reserved_quantity=new_reserved)
        await self.db.execute(stmt)
        await self.db.commit()
        
        return True

    async def consume_stock(self, product_id: int, location_id: int, quantity: Decimal) -> bool:
        """Consume stock (deduct from available quantity)"""
        stock_level = await self.get_stock_level(product_id, location_id)
        if not stock_level:
            return False
        
        available = stock_level.quantity - stock_level.reserved_quantity
        if available < quantity:
            raise InsufficientStockError(f"Insufficient stock: requested {quantity}, available {available}")
        
        # Update quantities
        stmt = update(StockLevel).where(
            and_(
                StockLevel.product_id == product_id,
                StockLevel.location_id == location_id
            )
        ).values(
            quantity=stock_level.quantity - quantity,
            reserved_quantity=max(0, stock_level.reserved_quantity - quantity)
        )
        await self.db.execute(stmt)
        await self.db.commit()
        
        return True