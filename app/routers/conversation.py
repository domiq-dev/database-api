"""
Property Management Chatbot - Conversation API Router

This module provides the REST API endpoints for managing conversations between
users and chatbots. It implements the primary business logic for lead capture
and qualification in the property management chatbot system.

Key Features:
- Atomic user and conversation creation
- Automatic user deduplication by email
- Chatbot validation and error handling
- Comprehensive lead data capture
- RESTful API design with proper HTTP status codes

Business Logic:
1. Validate chatbot exists and is active
2. Find existing user by email or create new user
3. Create conversation with all lead qualification data
4. Return structured response with IDs and status

Author: Development Team
Created: 2024
Last Modified: 2024
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models import User, Conversation, Chatbot
from app.schemas import ConversationCreateWithUser
import uuid

# Create router instance for conversation-related endpoints
router = APIRouter()


@router.post("/conversations/")
async def create_conversation_with_user(
        data: ConversationCreateWithUser,
        db: AsyncSession = Depends(get_db)
):
    """
    Create a conversation and automatically create or find the user
    
    This is the primary endpoint for chatbot integrations. It handles the complete
    workflow of user management and conversation creation in a single atomic operation.
    
    Business Logic Flow:
    1. Validate that the specified chatbot exists and is active
    2. If user_email is provided, search for existing user
    3. If no existing user found, create a new user record
    4. Create conversation record with all provided lead qualification data
    5. Return comprehensive response with IDs and metadata
    
    Key Features:
    - Atomic operation (both user and conversation created in single transaction)
    - User deduplication by email address
    - Support for anonymous users (no email required)
    - Comprehensive error handling with descriptive messages
    - Structured response for easy integration
    
    Args:
        data (ConversationCreateWithUser): Request payload containing user and conversation data
        db (AsyncSession): Database session injected by FastAPI dependency system
        
    Returns:
        dict: Response containing:
            - conversation_id: UUID of created conversation
            - user_id: UUID of user (existing or newly created)
            - user_email: Email address of user (if provided)
            - status: Current conversation status
            - lead_score: Calculated lead score
            - is_new_user: Boolean indicating if user was newly created
            - message: Success message
            
    Raises:
        HTTPException(404): If chatbot_id does not exist in database
        HTTPException(400): If chatbot is inactive or other validation errors
        HTTPException(500): If database operation fails
        
    Example Request:
        POST /conversations/
        {
            "chatbot_id": "550e8400-e29b-41d4-a716-446655440001",
            "user_email": "john@example.com",
            "user_first_name": "John",
            "user_last_name": "Doe",
            "is_qualified": true,
            "apartment_size_preference": "2br",
            "price_range_max": 2500.00
        }
        
    Example Response:
        {
            "conversation_id": "550e8400-e29b-41d4-a716-446655440003",
            "user_id": "550e8400-e29b-41d4-a716-446655440002",
            "user_email": "john@example.com",
            "status": "new",
            "lead_score": 0,
            "is_new_user": false,
            "message": "Conversation created successfully"
        }
    """

    # Step 1: Verify the chatbot exists and is active
    # This prevents conversations from being created for non-existent or inactive chatbots
    chatbot_result = await db.execute(
        select(Chatbot).where(Chatbot.id == data.chatbot_id)
    )
    chatbot = chatbot_result.scalar_one_or_none()

    # Return 404 if chatbot doesn't exist
    if not chatbot:
        raise HTTPException(
            status_code=404, 
            detail=f"Chatbot with id {data.chatbot_id} not found"
        )
    
    # Optional: Check if chatbot is active (uncomment if needed)
    # if not chatbot.is_active:
    #     raise HTTPException(
    #         status_code=400,
    #         detail=f"Chatbot {data.chatbot_id} is currently inactive"
    #     )

    # Step 2: Handle user creation or retrieval
    user = None
    
    # If email is provided, attempt to find existing user for deduplication
    if data.user_email:
        result = await db.execute(
            select(User).where(User.email == data.user_email)
        )
        user = result.scalar_one_or_none()

    # Step 3: Create new user if none found
    # This supports both anonymous users and email-based deduplication
    if not user:
        user = User(
            id=uuid.uuid4(),  # Generate new UUID for user
            first_name=data.user_first_name,
            last_name=data.user_last_name,
            email=data.user_email,
            phone=data.user_phone,
            age=data.user_age,
            lead_source=data.source or "Website Chat"  # Default lead source
        )
        # Add user to session but don't commit yet
        db.add(user)
        # Flush to get the user ID without committing the transaction
        await db.flush()

    # Step 4: Create the conversation record
    # This captures all the lead qualification data from the chatbot interaction
    conversation = Conversation(
        id=uuid.uuid4(),  # Generate new UUID for conversation
        chatbot_id=data.chatbot_id,
        user_id=user.id,
        
        # Lead qualification flags
        is_qualified=data.is_qualified,
        is_book_tour=data.is_book_tour,
        
        # Tour information
        tour_type=data.tour_type,
        tour_datetime=data.tour_datetime,
        
        # AI insights
        ai_intent_summary=data.ai_intent_summary,
        
        # Apartment preferences
        apartment_size_preference=data.apartment_size_preference,
        move_in_date=data.move_in_date,
        
        # Budget constraints
        price_range_min=data.price_range_min,
        price_range_max=data.price_range_max,
        
        # Household information
        occupants_count=data.occupants_count,
        has_pets=data.has_pets,
        pet_details=data.pet_details,
        
        # Preferences and requirements
        desired_features=data.desired_features,
        work_location=data.work_location,
        reason_for_moving=data.reason_for_moving,
        
        # Lead management fields
        pre_qualified=data.pre_qualified,
        source=data.source,
        status=data.status,
        notification_status=data.notification_status if data.notification_status is not None else {},
        lead_score=0  # Initial lead score (can be calculated by background job)
    )
    
    # Add conversation to session
    db.add(conversation)

    # Step 5: Commit both user and conversation atomically
    # This ensures data consistency - either both records are created or neither
    await db.commit()
    
    # Refresh models to get database-generated timestamps
    await db.refresh(user)
    await db.refresh(conversation)

    # Step 6: Return structured response
    # Provides all necessary information for the calling application
    return {
        "conversation_id": str(conversation.id),
        "user_id": str(user.id),
        "user_email": user.email,
        "status": conversation.status,
        "lead_score": conversation.lead_score,
        "is_new_user": user.created_at == user.updated_at,  # Check if timestamps are equal
        "message": "Conversation created successfully"
    }