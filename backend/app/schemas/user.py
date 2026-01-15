from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from .product import LocationResponse


class UserBase(BaseModel):
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str
    location_id: Optional[int] = None


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None
    location_id: Optional[int] = None


class UserResponse(UserBase):
    id: int
    is_superuser: bool
    location_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    location: Optional[LocationResponse] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class PermissionBase(BaseModel):
    resource: str
    action: str
    description: Optional[str] = None


class PermissionCreate(PermissionBase):
    pass


class PermissionResponse(PermissionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None
    scope: str = "global"  # 'global' or 'location'
    location_id: Optional[int] = None


class RoleCreate(RoleBase):
    permissions: List[int] = []  # List of permission IDs


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[str] = None
    location_id: Optional[int] = None
    permissions: Optional[List[int]] = None


class RoleResponse(RoleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    permissions: List[PermissionResponse] = []

    class Config:
        from_attributes = True


class UserRoleAssignmentBase(BaseModel):
    user_id: int
    role_id: int


class UserRoleAssignmentCreate(UserRoleAssignmentBase):
    pass


class UserRoleAssignmentResponse(UserRoleAssignmentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True