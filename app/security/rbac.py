from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User, Role, Permission, UserRoleAssignment, RolePermission
from app.security.auth import get_current_active_user


class PermissionChecker:
    """
    RBAC Permission Checker with Super Admin override
    If user.is_superuser is True, all permissions are granted automatically
    """
    
    def __init__(self, resource: str, action: str):
        self.resource = resource
        self.action = action

    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ):
        # Super admin has all permissions
        if current_user.is_superuser:
            return current_user
        
        # Check if user has the required permission
        has_permission = await self._check_user_permission(db, current_user.id, self.resource, self.action)
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {self.resource}.{self.action}"
            )
        
        return current_user

    async def _check_user_permission(
        self, 
        db: AsyncSession, 
        user_id: int, 
        resource: str, 
        action: str
    ) -> bool:
        """
        Check if user has a specific permission through their roles
        """
        # Query to check if user has the required permission
        stmt = (
            select(Permission)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .join(Role, RolePermission.role_id == Role.id)
            .join(UserRoleAssignment, Role.id == UserRoleAssignment.role_id)
            .where(UserRoleAssignment.user_id == user_id)
            .where(Permission.resource == resource)
            .where(Permission.action == action)
        )
        
        result = await db.execute(stmt)
        permission = result.scalar_one_or_none()
        
        return permission is not None


async def get_user_permissions(db: AsyncSession, user_id: int) -> List[str]:
    """
    Get all permissions for a user in the format 'resource.action'
    """
    stmt = (
        select(Permission)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .join(Role, RolePermission.role_id == Role.id)
        .join(UserRoleAssignment, Role.id == UserRoleAssignment.role_id)
        .where(UserRoleAssignment.user_id == user_id)
    )
    
    result = await db.execute(stmt)
    permissions = result.scalars().all()
    
    return [f"{perm.resource}.{perm.action}" for perm in permissions]


async def get_user_roles(db: AsyncSession, user_id: int) -> List[str]:
    """
    Get all roles assigned to a user
    """
    stmt = (
        select(Role.name)
        .join(UserRoleAssignment, Role.id == UserRoleAssignment.role_id)
        .where(UserRoleAssignment.user_id == user_id)
    )
    
    result = await db.execute(stmt)
    roles = result.scalars().all()
    
    return list(roles)


def require_permission(resource: str, action: str):
    """
    Convenience function to create a permission checker
    """
    return PermissionChecker(resource, action)


# Predefined permission checkers for common operations
require_stock_read = PermissionChecker("stock", "read")
require_stock_write = PermissionChecker("stock", "write")
require_stock_delete = PermissionChecker("stock", "delete")

require_product_read = PermissionChecker("product", "read")
require_product_write = PermissionChecker("product", "write")
require_product_delete = PermissionChecker("product", "delete")

require_user_manage = PermissionChecker("user", "manage")
require_role_manage = PermissionChecker("role", "manage")

require_audit_read = PermissionChecker("audit", "read")