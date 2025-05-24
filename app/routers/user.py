# user.py
"""
Property Management Chatbot - User API Router

This module provides REST API endpoints for user management operations.
Currently implements basic user creation functionality for backward compatibility
with existing integrations.

Note: This router is maintained for legacy support. New integrations should
use the conversation router's combined endpoint which handles user creation
automatically during conversation creation.

Author: Development Team
Created: 2024
Last Modified: 2024
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.schemas import UserCreate
from app.crud import create_user

# Create router instance for user-related endpoints
router = APIRouter()


@router.post("/users/")
async def new_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new user record
    
    This endpoint creates a new user from the provided user data.
    It's maintained for backward compatibility with existing integrations
    that manage users separately from conversations.
    
    For new integrations, consider using the conversation creation endpoint
    which handles user creation automatically and provides better atomicity.
    
    Args:
        user (UserCreate): User data from request body
        db (AsyncSession): Database session injected by dependency system
        
    Returns:
        User: Created user record with database-generated fields
        
    Raises:
        HTTPException(400): If email already exists (uniqueness constraint)
        HTTPException(422): If request data validation fails
        HTTPException(500): If database operation fails
        
    Example Request:
        POST /users/
        {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": "555-1234",
            "age": 30,
            "lead_source": "Facebook Ads"
        }
        
    Example Response:
        {
            "id": "550e8400-e29b-41d4-a716-446655440002",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": "555-1234",
            "age": 30,
            "lead_source": "Facebook Ads",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        }
    """
    # Delegate to CRUD function for actual user creation
    # This separation allows for reuse of user creation logic
    return await create_user(db, user)
