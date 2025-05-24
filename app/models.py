"""
Property Management Chatbot - Database Models

This module defines the SQLAlchemy ORM models for the property management chatbot system.
The models represent the core entities: Users, Chatbots, and Conversations.

Architecture:
- User: Represents potential tenants/leads who interact with chatbots
- Chatbot: AI assistants deployed on property websites to engage visitors
- Conversation: Records of interactions between users and chatbots, including lead qualification data

Database Design:
- Uses PostgreSQL with UUID primary keys for scalability
- Timezone-aware timestamps for audit trails
- JSON fields for flexible data storage (notifications, pet details, etc.)
- Foreign key relationships maintain data integrity

Author: Development Team
Created: 2024
Last Modified: 2024
"""

from sqlalchemy import Date, Column, String, Float, Integer, DateTime, Boolean, ForeignKey, Text, JSON, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime, timezone

# Create the base class for all ORM models
Base = declarative_base()


class User(Base):
    """
    User Model - Represents potential tenants/leads in the system
    
    This model stores information about users who interact with property chatbots.
    Users can be anonymous initially (minimal data) and provide more information
    as they engage with the chatbot and become qualified leads.
    
    Key Features:
    - Supports anonymous users (all fields except ID are optional)
    - Email uniqueness constraint for lead deduplication
    - Audit timestamps for tracking user lifecycle
    - Lead source tracking for marketing attribution
    
    Relationships:
    - One-to-many with Conversation (a user can have multiple conversations)
    """
    __tablename__ = "user"
    __table_args__ = {'extend_existing': True}

    # Primary key - UUID for scalability and security
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Personal information - all optional to support anonymous users
    first_name = Column(String(100), nullable=True, comment="User's first name")
    last_name = Column(String(100), nullable=True, comment="User's last name")
    
    # Contact information - email is unique for lead deduplication
    email = Column(String(255), unique=True, nullable=True, comment="User's email address - unique constraint for deduplication")
    phone = Column(String(20), nullable=True, comment="User's phone number")
    
    # Demographics
    age = Column(Integer, nullable=True, comment="User's age for demographic analysis")
    
    # Marketing attribution
    lead_source = Column(String(100), nullable=True, comment="Source of the lead (e.g., 'Facebook Ads', 'Google Search', 'Website Chat')")
    
    # Audit timestamps - timezone-aware for global deployments
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), comment="When the user record was created")
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="When the user record was last updated")


class Chatbot(Base):
    """
    Chatbot Model - Represents AI assistants deployed on property websites
    
    Each chatbot is associated with a specific property and contains configuration
    for how it should behave and appear to website visitors.
    
    Key Features:
    - Property-specific configuration
    - Customizable appearance (avatar, welcome message)
    - Widget embedding support
    - Active/inactive status for deployment control
    
    Relationships:
    - Many-to-one with Property (each chatbot belongs to one property)
    - One-to-many with Conversation (a chatbot can have multiple conversations)
    """
    __tablename__ = "chatbot"
    __table_args__ = {'extend_existing': True}

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to property - establishes which property this chatbot serves
    property_id = Column(UUID(as_uuid=True), nullable=False, comment="ID of the property this chatbot serves")
    
    # Chatbot configuration
    name = Column(String(100), nullable=False, comment="Display name of the chatbot")
    avatar_url = Column(String(255), nullable=True, comment="URL to chatbot's avatar image")
    is_active = Column(Boolean, default=True, comment="Whether this chatbot is currently active and accepting conversations")
    
    # Content configuration
    welcome_message = Column(Text, nullable=True, comment="Initial message shown to users when they start a conversation")
    
    # Technical configuration
    embed_code = Column(Text, nullable=True, comment="HTML/JavaScript code for embedding the chatbot widget")
    widget_settings = Column(JSON, nullable=True, comment="JSON configuration for widget appearance and behavior")
    
    # Audit timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), comment="When the chatbot was created")
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="When the chatbot was last updated")


class Conversation(Base):
    """
    Conversation Model - Records interactions between users and chatbots
    
    This is the core model that captures lead qualification data from chatbot interactions.
    It stores both the conversation metadata and the structured lead information
    extracted during the conversation.
    
    Key Features:
    - Lead qualification tracking (is_qualified, lead_score)
    - Tour booking information
    - Apartment preferences and requirements
    - Flexible JSON fields for extensibility
    - Status tracking for lead management workflow
    
    Relationships:
    - Many-to-one with User (each conversation belongs to one user)
    - Many-to-one with Chatbot (each conversation belongs to one chatbot)
    - One-to-many with Message (a conversation can have multiple messages)
    """
    __tablename__ = "conversation"
    __table_args__ = {'extend_existing': True}

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys establishing relationships
    chatbot_id = Column(UUID(as_uuid=True), ForeignKey("chatbot.id"), nullable=False, comment="ID of the chatbot handling this conversation")
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False, comment="ID of the user in this conversation")
    
    # Lead qualification flags
    is_qualified = Column(Boolean, default=False, comment="Whether this lead has been qualified as a potential tenant")
    is_book_tour = Column(Boolean, default=False, comment="Whether the user wants to book a tour")
    
    # Tour information
    tour_type = Column(String, nullable=True, comment="Type of tour requested (e.g., 'virtual', 'in-person', 'self-guided')")
    tour_datetime = Column(DateTime(timezone=False), nullable=True, comment="Requested date and time for the tour (stored as naive datetime)")
    
    # AI-generated insights
    ai_intent_summary = Column(String, nullable=True, comment="AI-generated summary of the user's intent and interests")
    
    # Apartment preferences
    apartment_size_preference = Column(String, nullable=True, comment="Preferred apartment size (e.g., 'studio', '1br', '2br')")
    move_in_date = Column(Date, nullable=True, comment="User's desired move-in date")
    
    # Budget information
    price_range_min = Column(Float, nullable=True, comment="Minimum budget for rent")
    price_range_max = Column(Float, nullable=True, comment="Maximum budget for rent")
    
    # Household information
    occupants_count = Column(Integer, nullable=True, comment="Number of people who will be living in the apartment")
    has_pets = Column(Boolean, nullable=True, comment="Whether the user has pets")
    pet_details = Column(JSON, nullable=True, comment="JSON object with pet details (type, breed, size, etc.)")
    
    # Preferences and requirements
    desired_features = Column(JSON, nullable=True, comment="JSON array of desired apartment features")
    work_location = Column(String, nullable=True, comment="User's work location for commute considerations")
    reason_for_moving = Column(String, nullable=True, comment="User's reason for moving")
    
    # Lead management
    pre_qualified = Column(Boolean, default=False, comment="Whether the user is pre-qualified for renting")
    source = Column(String, nullable=True, comment="Source of this conversation (e.g., 'Website Chat', 'Facebook Messenger')")
    status = Column(String, default="new", comment="Current status of the lead (e.g., 'new', 'qualified', 'tour_scheduled', 'closed')")
    notification_status = Column(JSON, default={}, comment="JSON object tracking notification delivery status")
    lead_score = Column(Integer, default=0, comment="Calculated lead score based on qualification criteria")
    
    # Audit timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), comment="When the conversation was started")
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="When the conversation was last updated")