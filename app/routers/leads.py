"""
Leads Router - Frontend Integration

This module provides endpoints for the Next.js frontend to manage leads.
Maps frontend Lead interface to backend Conversation/User models.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from app.db import get_db
from app.models import (
    User, Conversation, Message,
    PropertyManagerAssignment, Property,
    Chatbot, FAQ
)
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, date
from uuid import UUID
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models matching your frontend interface
class LeadUser(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    lead_source: str

class LeadConversation(BaseModel):
    chatbot_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    is_book_tour: bool
    apartment_size_preference: Optional[str] = None
    price_range_min: Optional[int] = None
    price_range_max: Optional[int] = None
    tour_type: Optional[str] = None
    tour_datetime: Optional[datetime] = None
    move_in_date: Optional[date] = None
    is_qualified: Optional[bool] = None
    ai_intent_summary: Optional[str] = None
    kb_pending: Optional[str] = None

class LeadMessage(BaseModel):
    sender_type: str  # 'user' or 'bot'
    message_text: str
    timestamp: datetime

class LeadSubmission(BaseModel):
    user: LeadUser
    conversation: LeadConversation
    messages: List[LeadMessage]

class LeadResponse(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    current_stage: str
    source: str
    created_at: datetime
    last_activity: datetime
    assigned_agent: Optional[str] = None
    unit_interest: Optional[str] = None
    property_name: Optional[str] = None

class LeadTimelineItem(BaseModel):
    id: str
    type: str
    timestamp: datetime
    details: Dict[str, Any]
    created_by: str

@router.post("/leads/", response_model=Dict[str, Any])
async def create_lead(
    lead_data: LeadSubmission,
    db: AsyncSession = Depends(get_db)
):
    """
    Create new lead from frontend chat submission
    
    This endpoint receives lead data from your Next.js frontend and creates
    the necessary User, Conversation, and Message records in the database.
    """
    
    try:
        # 1. Create or get existing user
        user = None
        if lead_data.user.email:
            # Check if user exists
            result = await db.execute(
                select(User).where(User.email == lead_data.user.email)
            )
            user = result.scalar_one_or_none()
        
        if not user:
            # Create new user
            user = User(
                first_name=lead_data.user.first_name or "Anonymous",
                last_name=lead_data.user.last_name or "User",
                email=lead_data.user.email,
                phone=lead_data.user.phone,
                lead_source=lead_data.user.lead_source,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(user)
            await db.flush()  # Get the user ID
        
        # 2. Create conversation
        conversation = Conversation(
            user_id=user.id,
            chatbot_id=UUID(lead_data.conversation.chatbot_id),
            start_time=lead_data.conversation.start_time,
            end_time=lead_data.conversation.end_time,
            is_book_tour=lead_data.conversation.is_book_tour,
            status='active' if not lead_data.conversation.end_time else 'completed',
            is_qualified=bool(lead_data.conversation.is_qualified),
            ai_intent_summary=lead_data.conversation.ai_intent_summary,
            apartment_size_preference=lead_data.conversation.apartment_size_preference,
            price_range_min=lead_data.conversation.price_range_min,
            price_range_max=lead_data.conversation.price_range_max,
            tour_type=lead_data.conversation.tour_type,
            tour_datetime=lead_data.conversation.tour_datetime,
            move_in_date=lead_data.conversation.move_in_date,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(conversation)
        await db.flush()  # Get the conversation ID
        
        # ------------------------------------------------------------------
        # 3.  If the visitor asked an unanswered question, save it in `faq`
        # ------------------------------------------------------------------
        if lead_data.conversation.kb_pending:
            # derive the property from the chatbot
            result = await db.execute(
                select(Chatbot.property_id)
                .where(Chatbot.id == UUID(lead_data.conversation.chatbot_id))
            )
            property_id = result.scalar_one_or_none()

            faq_item = FAQ(
                property_id=property_id,
                question=lead_data.conversation.kb_pending,
                answer=None,           # no answer yet
                category=None,
                source_type=None       # unknown at this stage
            )
            db.add(faq_item)
        
        # 4. Create messages
        for msg_data in lead_data.messages:
            message = Message(
                conversation_id=conversation.id,
                sender_type=msg_data.sender_type,
                message_text=msg_data.message_text,
                timestamp=msg_data.timestamp
            )
            db.add(message)
        
        # 5. Commit all changes
        await db.commit()
        
        # 6. Return lead summary
        lead_stage = _determine_lead_stage(conversation, user)
        
        return {
            "success": True,
            "lead_id": str(conversation.id),
            "user_id": str(user.id),
            "stage": lead_stage,
            "qualified": conversation.is_qualified,
            "tour_booked": conversation.is_book_tour,
            "message": "Lead created successfully"
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating lead: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create lead: {str(e)}")

@router.get("/leads/", response_model=Dict[str, Any])
async def get_leads(
    manager_email: Optional[str] = Query(None),
    property_id: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db)
):
    """
    Get leads for dashboard - filtered by manager permissions
    
    This endpoint returns leads that the authenticated manager can access
    based on their property assignments.
    """
    
    try:
        # Build base query
        query = select(
            Conversation,
            User,
            Property.name.label('property_name')
        ).select_from(
            Conversation
        ).join(
            User, Conversation.user_id == User.id
        ).join(
            # Join through chatbot to get property
            Property, Conversation.chatbot_id.in_(
                select(Property.id)  # Simplified - in real app, join through Chatbot table
            ), isouter=True
        )
        
        # Filter by manager permissions if provided
        if manager_email:
            # Get manager's assigned properties
            manager_properties_subquery = select(
                PropertyManagerAssignment.property_id
            ).select_from(
                PropertyManagerAssignment
            ).join(
                PropertyManager, PropertyManagerAssignment.property_manager_id == PropertyManager.id
            ).where(
                PropertyManager.email == manager_email,
                PropertyManagerAssignment.end_date.is_(None)
            )
            
            query = query.where(
                Property.id.in_(manager_properties_subquery)
            )
        
        # Filter by specific property if provided
        if property_id:
            query = query.where(Property.id == UUID(property_id))
        
        # Filter by stage if provided
        if stage:
            conversation_status = _stage_to_status(stage)
            query = query.where(Conversation.status == conversation_status)
        
        # Add ordering and pagination
        query = query.order_by(Conversation.created_at.desc())
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        rows = result.all()
        
        # Transform to frontend format
        leads = []
        for conversation, user, property_name in rows:
            lead_stage = _determine_lead_stage(conversation, user)
            user_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            if not user_name:
                user_name = "Anonymous User"
            
            lead = LeadResponse(
                id=str(conversation.id),
                name=user_name,
                email=user.email,
                phone=user.phone,
                current_stage=lead_stage,
                source=user.lead_source or 'chat',
                created_at=conversation.created_at,
                last_activity=conversation.updated_at,
                unit_interest=conversation.apartment_size_preference,
                property_name=property_name
            )
            leads.append(lead.dict())
        
        # Get total count for pagination
        count_query = select(func.count(Conversation.id)).select_from(Conversation)
        if manager_email:
            count_query = count_query.where(
                Property.id.in_(manager_properties_subquery)
            )
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        return {
            "leads": leads,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error fetching leads: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch leads: {str(e)}")

@router.get("/leads/{lead_id}", response_model=Dict[str, Any])
async def get_lead_details(
    lead_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information for a specific lead"""
    
    try:
        # Get conversation with user and messages
        result = await db.execute(
            select(Conversation, User).join(User)
            .where(Conversation.id == UUID(lead_id))
        )
        row = result.first()
        
        if not row:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        conversation, user = row
        
        # Get messages
        messages_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.timestamp)
        )
        messages = messages_result.scalars().all()
        
        # Build timeline
        timeline = []
        
        # Add chat initiated
        timeline.append({
            "id": f"chat_{conversation.id}",
            "type": "chat_initiated",
            "timestamp": conversation.start_time,
            "details": {
                "message_count": len(messages)
            },
            "created_by": "system"
        })
        
        # Add info collected if we have contact info
        if user.email or user.phone:
            timeline.append({
                "id": f"info_{conversation.id}",
                "type": "info_collected", 
                "timestamp": conversation.start_time,  # Approximate
                "details": {
                    "email": user.email,
                    "phone": user.phone
                },
                "created_by": "ai"
            })
        
        # Fix timezone issue in timeline creation
        if conversation.tour_datetime:
            # Ensure timezone-aware datetime for timeline
            tour_time = conversation.tour_datetime
            if tour_time.tzinfo is None:
                tour_time = tour_time.replace(tzinfo=timezone.utc)
                
            timeline.append({
                "id": f"tour_{conversation.id}",
                "type": "tour_scheduled",
                "timestamp": tour_time,
                "details": {
                    "tour_type": conversation.tour_type,
                    "tour_date": tour_time
                },
                "created_by": "agent"
            })
        
        return {
            "id": str(conversation.id),
            "name": f"{user.first_name or ''} {user.last_name or ''}".strip() or "Anonymous User",
            "email": user.email,
            "phone": user.phone,
            "current_stage": _determine_lead_stage(conversation, user),
            "source": user.lead_source or 'chat',
            "created_at": conversation.created_at,
            "last_activity": conversation.updated_at,
            "unit_interest": conversation.apartment_size_preference,
            "timeline": timeline,
            "messages": [
                {
                    "sender_type": msg.sender_type,
                    "message_text": msg.message_text,
                    "timestamp": msg.timestamp
                }
                for msg in messages
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching lead details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch lead details: {str(e)}")

def _determine_lead_stage(conversation: Conversation, user: User) -> str:
    """Determine lead stage based on conversation and user data"""
    
    if conversation.status == 'closed':
        return 'handed_off'
    elif conversation.is_book_tour and conversation.tour_datetime:
        # Fix: Ensure both datetimes are timezone-aware for comparison
        now_utc = datetime.now(timezone.utc)
        tour_time = conversation.tour_datetime
        
        # If tour_datetime is naive, assume it's UTC
        if tour_time.tzinfo is None:
            tour_time = tour_time.replace(tzinfo=timezone.utc)
            
        if tour_time < now_utc:
            return 'tour_completed'
        else:
            return 'tour_scheduled'
    elif user.email or user.phone:
        return 'info_collected'
    else:
        return 'chat_initiated'

def _stage_to_status(stage: str) -> str:
    """Convert frontend stage to backend conversation status"""
    
    stage_mapping = {
        'chat_initiated': 'active',
        'info_collected': 'qualified',
        'tour_scheduled': 'tour_booked',
        'tour_completed': 'tour_completed',
        'handed_off': 'closed'
    }
    return stage_mapping.get(stage, 'active') 