"""
Property Management Chatbot - CRUD Operations

This module contains Create, Read, Update, Delete (CRUD) operations for the
property management chatbot system. These functions provide a data access
layer between the API endpoints and the database models.

Current Implementation:
- Basic create operations for User and Conversation models
- Async/await pattern for non-blocking database operations
- SQLAlchemy ORM integration

Future Enhancements:
- Read operations with filtering and pagination
- Update operations for lead management
- Delete operations with soft delete support
- Bulk operations for data migration

Author: Development Team
Created: 2024
Last Modified: 2024
"""

from sqlalchemy.ext.asyncio import AsyncSession
from .models import User, Conversation
from .schemas import UserCreate, ConversationCreate


async def create_user(db: AsyncSession, user: UserCreate):
    """
    Create a new user record in the database
    
    This function creates a new user from the provided UserCreate schema.
    It's primarily used for backward compatibility with existing integrations
    that create users separately from conversations.
    
    Note: For new integrations, consider using the combined conversation
    creation endpoint which handles user creation automatically.
    
    Args:
        db (AsyncSession): Database session for the operation
        user (UserCreate): Pydantic model containing user data
        
    Returns:
        User: The created user model with database-generated fields (id, timestamps)
        
    Raises:
        SQLAlchemyError: If database operation fails
        IntegrityError: If email uniqueness constraint is violated
        
    Example:
        user_data = UserCreate(
            first_name="John",
            last_name="Doe", 
            email="john@example.com"
        )
        new_user = await create_user(db, user_data)
    """
    # Convert Pydantic model to SQLAlchemy model
    # .dict() extracts all fields as a dictionary for model creation
    db_user = User(**user.dict())
    
    # Add the new user to the session (stages for commit)
    db.add(db_user)
    
    # Commit the transaction to persist changes to database
    await db.commit()
    
    # Refresh the model to get database-generated fields (id, timestamps)
    await db.refresh(db_user)
    
    return db_user


async def create_conversation(db: AsyncSession, convo: ConversationCreate):
    """
    Create a new conversation record in the database
    
    This function creates a conversation from the provided ConversationCreate schema.
    It requires that both the user and chatbot already exist in the database.
    
    Note: This is a legacy function maintained for backward compatibility.
    New integrations should use the combined conversation creation endpoint
    in the conversation router which handles user creation automatically.
    
    Args:
        db (AsyncSession): Database session for the operation
        convo (ConversationCreate): Pydantic model containing conversation data
        
    Returns:
        Conversation: The created conversation model with database-generated fields
        
    Raises:
        SQLAlchemyError: If database operation fails
        ForeignKeyError: If user_id or chatbot_id references don't exist
        
    Example:
        convo_data = ConversationCreate(
            chatbot_id="550e8400-e29b-41d4-a716-446655440001",
            user_id="550e8400-e29b-41d4-a716-446655440002",
            is_qualified=True,
            ai_intent_summary="User looking for 2BR apartment"
        )
        new_conversation = await create_conversation(db, convo_data)
    """
    # Convert Pydantic model to SQLAlchemy model
    # .dict() extracts all fields as a dictionary for model creation
    db_convo = Conversation(**convo.dict())
    
    # Add the new conversation to the session (stages for commit)
    db.add(db_convo)
    
    # Commit the transaction to persist changes to database
    await db.commit()
    
    # Refresh the model to get database-generated fields (id, timestamps)
    await db.refresh(db_convo)
    
    return db_convo
