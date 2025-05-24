from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models import User, Conversation, Chatbot
from app.schemas import ConversationCreateWithUser
import uuid

router = APIRouter()

@router.post("/conversations/")
async def create_conversation_with_user(
        data: ConversationCreateWithUser,
        db: AsyncSession = Depends(get_db)
):
    """
    Create a conversation and automatically create or find the user.
    This is the single endpoint you need for the chatbot interaction.
    """

    # First, verify the chatbot exists
    chatbot_result = await db.execute(
        select(Chatbot).where(Chatbot.id == data.chatbot_id)
    )
    chatbot = chatbot_result.scalar_one_or_none()

    if not chatbot:
        raise HTTPException(status_code=404, detail=f"Chatbot with id {data.chatbot_id} not found")

    # Check if user exists by email (if provided)
    user = None
    if data.user_email:
        result = await db.execute(
            select(User).where(User.email == data.user_email)
        )
        user = result.scalar_one_or_none()

    # If no user found, create a new one
    if not user:
        user = User(
            id=uuid.uuid4(),
            first_name=data.user_first_name,
            last_name=data.user_last_name,
            email=data.user_email,
            phone=data.user_phone,
            age=data.user_age,
            lead_source=data.source or "Website Chat"
        )
        db.add(user)
        await db.flush()  # Get the user ID without committing

    # Create the conversation
    conversation = Conversation(
        id=uuid.uuid4(),
        chatbot_id=data.chatbot_id,
        user_id=user.id,
        is_qualified=data.is_qualified,
        is_book_tour=data.is_book_tour,
        tour_type=data.tour_type,
        tour_datetime=data.tour_datetime,
        ai_intent_summary=data.ai_intent_summary,
        apartment_size_preference=data.apartment_size_preference,
        move_in_date=data.move_in_date,
        price_range_min=data.price_range_min,
        price_range_max=data.price_range_max,
        occupants_count=data.occupants_count,
        has_pets=data.has_pets,
        pet_details=data.pet_details,
        desired_features=data.desired_features,
        work_location=data.work_location,
        reason_for_moving=data.reason_for_moving,
        pre_qualified=data.pre_qualified,
        source=data.source,
        status=data.status,
        notification_status=data.notification_status if data.notification_status is not None else {},
        lead_score=0
    )
    db.add(conversation)

    # Commit both user and conversation
    await db.commit()
    await db.refresh(user)
    await db.refresh(conversation)

    return {
        "conversation_id": str(conversation.id),
        "user_id": str(user.id),
        "user_email": user.email,
        "status": conversation.status,
        "lead_score": conversation.lead_score,
        "is_new_user": user.created_at == user.updated_at,
        "message": "Conversation created successfully"
    }