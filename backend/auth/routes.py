"""
Authentication API Routes
Handles user authentication, registration, and token management
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db.models import User
from .jwt import (
    authenticate_user, create_user_tokens, get_current_active_user,
    get_current_admin_user, refresh_access_token, get_password_hash,
    require_permission, check_permission
)

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Pydantic models for request/response
class UserLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, regex="^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)
    role: str = Field(default="user", regex="^(user|officer|admin)$")
    badge_number: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, max_length=50)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    permissions: Optional[list]

class UserProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=50)

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """User login endpoint"""
    logger.info(f"Login attempt for user: {login_data.username}")
    
    # Authenticate user
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        logger.warning(f"Failed login attempt for user: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    tokens = create_user_tokens(user)
    
    logger.info(f"Successful login for user: {login_data.username}")
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=30 * 60,  # 30 minutes in seconds
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "permissions": user.permissions or []
        }
    )

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Register new user (admin only)"""
    logger.info(f"Registration attempt for user: {user_data.username} by admin: {current_user.username}")
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role,
        badge_number=user_data.badge_number,
        department=user_data.department,
        is_active=True,
        created_at=datetime.utcnow(),
        permissions=get_default_permissions(user_data.role)
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"Successfully registered user: {user_data.username}")
    
    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
        last_login=new_user.last_login,
        permissions=new_user.permissions
    )

@router.post("/refresh")
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token"""
    logger.info("Token refresh attempt")
    
    try:
        # Refresh access token
        new_tokens = await refresh_access_token(refresh_data.refresh_token, db)
        
        logger.info("Token refresh successful")
        
        return {
            "access_token": new_tokens["access_token"],
            "token_type": new_tokens["token_type"],
            "expires_in": 30 * 60  # 30 minutes in seconds
        }
        
    except HTTPException as e:
        logger.warning(f"Token refresh failed: {e.detail}")
        raise e

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
        permissions=current_user.permissions
    )

@router.put("/me", response_model=UserResponse)
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    logger.info(f"Profile update for user: {current_user.username}")
    
    # Update fields if provided
    if profile_data.email is not None:
        # Check if email already exists (excluding current user)
        existing_email = db.query(User).filter(
            User.email == profile_data.email,
            User.id != current_user.id
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        current_user.email = profile_data.email
    
    if profile_data.full_name is not None:
        current_user.full_name = profile_data.full_name
    
    if profile_data.department is not None:
        current_user.department = profile_data.department
    
    db.commit()
    db.refresh(current_user)
    
    logger.info(f"Profile updated for user: {current_user.username}")
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
        permissions=current_user.permissions
    )

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    logger.info(f"Password change for user: {current_user.username}")
    
    # Verify current password
    from .jwt import verify_password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    logger.info(f"Password changed for user: {current_user.username}")
    
    return {"message": "Password changed successfully"}

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login,
            permissions=user.permissions
        )
        for user in users
    ]

@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_active: bool,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update user status (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = is_active
    db.commit()
    
    logger.info(f"User {user.username} status changed to {'active' if is_active else 'inactive'} by {current_user.username}")
    
    return {"message": f"User status updated to {'active' if is_active else 'inactive'}"}

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    db.delete(user)
    db.commit()
    
    logger.info(f"User {user.username} deleted by {current_user.username}")
    
    return {"message": "User deleted successfully"}

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """User logout"""
    logger.info(f"Logout for user: {current_user.username}")
    
    # In a real implementation, you might want to:
    # - Blacklist the token
    # - Clear session data
    # - Log the logout event
    
    return {"message": "Logout successful"}

def get_default_permissions(role: str) -> list:
    """Get default permissions for a role"""
    permissions = {
        "user": [
            "read:own_profile",
            "update:own_profile",
            "read:alerts",
            "read:journeys"
        ],
        "officer": [
            "read:own_profile",
            "update:own_profile",
            "read:alerts",
            "update:alerts",
            "read:journeys",
            "read:zones",
            "create:feedback"
        ],
        "admin": [
            "*"  # All permissions
        ]
    }
    
    return permissions.get(role, [])