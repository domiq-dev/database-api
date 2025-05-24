from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date
import uuid


class UserCreate(BaseModel):
    """Keep this for backward compatibility if needed"""
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[EmailStr]
    phone: Optional[str]
    age: Optional[int]
    lead_source: Optional[str]


class ConversationCreate(BaseModel):
    """Keep this for backward compatibility if needed"""
    chatbot_id: UUID
    user_id: UUID
    is_qualified: Optional[bool] = False
    is_book_tour: Optional[bool] = False
    tour_type: Optional[str] = None
    tour_datetime: Optional[datetime] = None
    ai_intent_summary: Optional[str] = None
    apartment_size_preference: Optional[str] = None
    move_in_date: Optional[date] = None
    price_range_min: Optional[float] = None
    price_range_max: Optional[float] = None
    occupants_count: Optional[int] = None
    has_pets: Optional[bool] = None
    pet_details: Optional[dict] = None
    desired_features: Optional[List[str]] = None
    work_location: Optional[str] = None
    reason_for_moving: Optional[str] = None
    pre_qualified: Optional[bool] = False
    source: Optional[str] = None
    status: Optional[str] = "new"
    notification_status: Optional[dict] = {}
    lead_score: Optional[int] = 0

    @field_validator('chatbot_id', 'user_id', mode='before')
    def convert_to_uuid(cls, v):
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                return UUID(hex=uuid.uuid5(uuid.NAMESPACE_DNS, v).hex)
        return v

    @field_validator('tour_datetime', mode='before')
    def convert_to_naive_datetime(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
            return dt.replace(tzinfo=None)
        elif isinstance(v, datetime) and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v


class ConversationCreateWithUser(BaseModel):
    """New combined schema for creating both user and conversation"""

    # Chatbot info (required)
    chatbot_id: UUID

    # User info (all optional since users might be anonymous initially)
    user_email: Optional[EmailStr] = None
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    user_phone: Optional[str] = None
    user_age: Optional[int] = None

    # Conversation info
    is_qualified: Optional[bool] = False
    is_book_tour: Optional[bool] = False
    tour_type: Optional[str] = None
    tour_datetime: Optional[datetime] = None
    ai_intent_summary: Optional[str] = None
    apartment_size_preference: Optional[str] = None
    move_in_date: Optional[date] = None
    price_range_min: Optional[float] = None
    price_range_max: Optional[float] = None
    occupants_count: Optional[int] = None
    has_pets: Optional[bool] = None
    pet_details: Optional[dict] = None
    desired_features: Optional[List[str]] = None
    work_location: Optional[str] = None
    reason_for_moving: Optional[str] = None
    pre_qualified: Optional[bool] = False
    source: Optional[str] = "Website Chat"
    status: Optional[str] = "new"
    notification_status: Optional[dict] = None
    lead_score: Optional[int] = None

    @field_validator('chatbot_id', mode='before')
    def convert_chatbot_id_to_uuid(cls, v):
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                raise ValueError(f"Invalid UUID format for chatbot_id: {v}")
        return v

    @field_validator('tour_datetime', mode='before')
    def convert_to_naive_datetime(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
            return dt.replace(tzinfo=None)
        elif isinstance(v, datetime) and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v