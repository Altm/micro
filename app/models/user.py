from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)  # Super admin flag
    location_id = Column(Integer, ForeignKey("locations.id"))  # For location-specific users
    
    # Relationships
    location = relationship("Location", back_populates="users")
    role_assignments = relationship("UserRoleAssignment", back_populates="user")


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255))
    scope = Column(String(20), default="global")  # 'global' or 'location'
    location_id = Column(Integer, ForeignKey("locations.id"))  # Nullable for global roles
    
    # Relationships
    permissions = relationship("RolePermission", back_populates="role")
    assignments = relationship("UserRoleAssignment", back_populates="role")
    location = relationship("Location")


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    resource = Column(String(50), nullable=False)  # e.g., 'stock', 'product', 'user'
    action = Column(String(50), nullable=False)    # e.g., 'read', 'write', 'delete'
    description = Column(String(255))
    
    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission")


class UserRoleAssignment(Base, TimestampMixin):
    __tablename__ = "user_role_assignments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="role_assignments")
    role = relationship("Role", back_populates="assignments")


class RolePermission(Base, TimestampMixin):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)
    
    # Relationships
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="role_permissions")