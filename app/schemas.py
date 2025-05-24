"""
Property Management Chatbot - Pydantic Schemas

This module defines the Pydantic models used for API request/response validation
and serialization. These schemas ensure data integrity and provide automatic
API documentation through FastAPI.

Schema Categories:
1. Legacy Schemas: Backward compatibility for existing integrations
2. Combined Schemas: New unified schemas for streamlined API usage
3. Validation Logic: Custom validators for data transformation and validation

Key Features:
- Automatic UUID conversion and validation
- Timezone-aware datetime handling
- Optional field support for flexible data collection
- Field validation with descriptive error messages

Author: Development Team
Created: 2024
Last Modified: 2024
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date
import uuid


class UserCreate(BaseModel):
    """
    Legacy User Creation Schema
    
    This schema is maintained for backward compatibility with existing integrations.
    Use ConversationCreateWithUser for new implementations as it provides a more
    streamlined approach to user and conversation creation.
    
    All fields are optional to support anonymous user creation, which is common
    in chatbot interactions where users may provide information gradually.
    """
    
    # Personal information - optional for anonymous users
    first_name: Optional[str] = None  # User's first name
    last_name: Optional[str] = None   # User's last name
    
    # Contact information
    email: Optional[EmailStr] = None  # Email with automatic validation
    phone: Optional[str] = None       # Phone number as string for flexibility
    
    # Demographics
    age: Optional[int] = None         # User's age for demographic analysis
    
    # Marketing attribution
    lead_source: Optional[str] = None # Source of the lead for marketing attribution


class ConversationCreate(BaseModel):
    """
    Legacy Conversation Creation Schema
    
    This schema is maintained for backward compatibility. It requires separate
    user creation before conversation creation. For new implementations,
    use ConversationCreateWithUser which handles both operations atomically.
    
    Contains comprehensive lead qualification fields to capture all relevant
    information from chatbot interactions.
    """
    
    # Required relationships
    chatbot_id: UUID  # ID of the chatbot handling this conversation
    user_id: UUID     # ID of the user (must exist before conversation creation)
    
    # Lead qualification
    is_qualified: Optional[bool] = False      # Whether this is a qualified lead
    is_book_tour: Optional[bool] = False      # Whether user wants to book a tour
    
    # Tour details
    tour_type: Optional[str] = None           # Type of tour (virtual, in-person, etc.)
    tour_datetime: Optional[datetime] = None  # Requested tour date/time
    
    # AI insights
    ai_intent_summary: Optional[str] = None   # AI-generated summary of user intent
    
    # Apartment preferences
    apartment_size_preference: Optional[str] = None  # Preferred apartment size
    move_in_date: Optional[date] = None              # Desired move-in date
    
    # Budget constraints
    price_range_min: Optional[float] = None   # Minimum budget
    price_range_max: Optional[float] = None   # Maximum budget
    
    # Household information
    occupants_count: Optional[int] = None     # Number of occupants
    has_pets: Optional[bool] = None           # Whether user has pets
    pet_details: Optional[dict] = None        # Pet information as flexible JSON
    
    # Preferences
    desired_features: Optional[List[str]] = None  # List of desired apartment features
    work_location: Optional[str] = None           # Work location for commute planning
    reason_for_moving: Optional[str] = None       # Reason for moving
    
    # Lead management
    pre_qualified: Optional[bool] = False     # Pre-qualification status
    source: Optional[str] = None              # Conversation source
    status: Optional[str] = "new"             # Lead status
    notification_status: Optional[dict] = {}  # Notification tracking
    lead_score: Optional[int] = 0             # Calculated lead score

    @field_validator('chatbot_id', 'user_id', mode='before')
    def convert_to_uuid(cls, v):
        """
        Convert string UUIDs to UUID objects with fallback generation
        
        This validator handles cases where UUIDs are provided as strings
        and ensures they are properly converted to UUID objects. If the
        string is not a valid UUID, it generates a deterministic UUID
        using the DNS namespace.
        
        Args:
            v: The value to convert (string or UUID)
            
        Returns:
            UUID: A valid UUID object
        """
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                # Generate deterministic UUID for invalid strings
                return UUID(hex=uuid.uuid5(uuid.NAMESPACE_DNS, v).hex)
        return v

    @field_validator('tour_datetime', mode='before')
    def convert_to_naive_datetime(cls, v):
        """
        Convert timezone-aware datetimes to naive datetimes
        
        The database stores tour_datetime as timezone-naive to simplify
        scheduling logic. This validator ensures all datetime inputs
        are converted to naive datetimes, removing timezone information.
        
        Args:
            v: The datetime value to convert
            
        Returns:
            datetime: A naive datetime object or None
        """
        if v is None:
            return v
        if isinstance(v, str):
            # Parse ISO format strings and convert to naive
            dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
            return dt.replace(tzinfo=None)
        elif isinstance(v, datetime) and v.tzinfo is not None:
            # Remove timezone info from timezone-aware datetimes
            return v.replace(tzinfo=None)
        return v


class ConversationCreateWithUser(BaseModel):
    """
    Combined User and Conversation Creation Schema
    
    This is the primary schema for new integrations. It allows atomic creation
    of both user and conversation records in a single API call, which is ideal
    for chatbot interactions where user information is collected during the
    conversation.
    
    Key Benefits:
    - Atomic operation (both user and conversation created together)
    - Handles anonymous users gracefully
    - Automatic user deduplication by email
    - Comprehensive lead qualification data capture
    - Simplified API integration
    
    Usage Pattern:
    1. Chatbot collects information during conversation
    2. Single API call creates/finds user and creates conversation
    3. All lead qualification data is captured in one operation
    """

    # Required: Chatbot identification
    chatbot_id: UUID  # ID of the chatbot handling this conversation

    # User information (all optional for anonymous users)
    user_email: Optional[EmailStr] = None      # Email for user deduplication
    user_first_name: Optional[str] = None      # User's first name
    user_last_name: Optional[str] = None       # User's last name
    user_phone: Optional[str] = None           # User's phone number
    user_age: Optional[int] = None             # User's age

    # Lead qualification flags
    is_qualified: Optional[bool] = False       # Whether this is a qualified lead
    is_book_tour: Optional[bool] = False       # Whether user wants to book a tour

    # Tour information
    tour_type: Optional[str] = None            # Type of tour requested
    tour_datetime: Optional[datetime] = None   # Requested tour date/time

    # AI-generated insights
    ai_intent_summary: Optional[str] = None    # AI summary of user intent

    # Apartment preferences
    apartment_size_preference: Optional[str] = None  # Preferred size
    move_in_date: Optional[date] = None              # Desired move-in date

    # Budget information
    price_range_min: Optional[float] = None    # Minimum budget
    price_range_max: Optional[float] = None    # Maximum budget

    # Household details
    occupants_count: Optional[int] = None      # Number of occupants
    has_pets: Optional[bool] = None            # Pet ownership
    pet_details: Optional[dict] = None         # Pet details as JSON

    # Preferences and requirements
    desired_features: Optional[List[str]] = None  # Desired apartment features
    work_location: Optional[str] = None           # Work location
    reason_for_moving: Optional[str] = None       # Reason for moving

    # Lead management
    pre_qualified: Optional[bool] = False         # Pre-qualification status
    source: Optional[str] = "Website Chat"        # Default source
    status: Optional[str] = "new"                 # Initial status
    notification_status: Optional[dict] = None    # Notification tracking
    lead_score: Optional[int] = None              # Lead score

    @field_validator('chatbot_id', mode='before')
    def convert_chatbot_id_to_uuid(cls, v):
        """
        Validate and convert chatbot_id to UUID
        
        Ensures the chatbot_id is a valid UUID. Unlike the legacy validator,
        this one raises a clear error for invalid UUIDs rather than generating
        a fallback UUID, as chatbot_id must reference an existing chatbot.
        
        Args:
            v: The chatbot_id value to validate
            
        Returns:
            UUID: A valid UUID object
            
        Raises:
            ValueError: If the UUID format is invalid
        """
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                raise ValueError(f"Invalid UUID format for chatbot_id: {v}")
        return v

    @field_validator('tour_datetime', mode='before')
    def convert_to_naive_datetime(cls, v):
        """
        Convert timezone-aware datetimes to naive datetimes
        
        Identical to the legacy validator - ensures tour_datetime is stored
        as a naive datetime for consistent database storage and retrieval.
        
        Args:
            v: The datetime value to convert
            
        Returns:
            datetime: A naive datetime object or None
        """
        if v is None:
            return v
        if isinstance(v, str):
            # Parse ISO format and convert to naive
            dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
            return dt.replace(tzinfo=None)
        elif isinstance(v, datetime) and v.tzinfo is not None:
            # Remove timezone information
            return v.replace(tzinfo=None)
        return v