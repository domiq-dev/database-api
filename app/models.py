"""
Property Management Chatbot - Database Models

This module defines the SQLAlchemy ORM models for the property management chatbot system.
The models represent the core entities: Users, Chatbots, Conversations, Companies, Properties, and Property Managers.

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
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone

# Create the base class for all ORM models
Base = declarative_base()


class Company(Base):
    """
    Company Model - Represents property management companies
    """
    __tablename__ = "company"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Company information - matching actual database schema
    name = Column(String(255), nullable=False, unique=True, comment="Company name")
    logo_url = Column(String(255), nullable=True, comment="Company logo URL")
    contact_email = Column(String(255), nullable=True, comment="Primary contact email")
    contact_phone = Column(String(20), nullable=True, comment="Company phone number")
    hubspot_company_id = Column(String(100), nullable=True, comment="HubSpot company ID for integration")
    
    # Audit timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), comment="When the company was created")
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="When the company was last updated")


class Property(Base):
    """
    Property Model - Represents individual properties/buildings
    """
    __tablename__ = "property"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to company
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id"), nullable=False, comment="ID of the company that owns this property")
    
    # Property information - matching database schema
    name = Column(String(255), nullable=False, comment="Property name")
    address = Column(String(255), nullable=False, comment="Property address")
    city = Column(String(100), nullable=False, comment="Property city")
    state = Column(String(50), nullable=False, comment="Property state")
    zip_code = Column(String(20), nullable=False, comment="Property zip code")
    property_type = Column(String(50), nullable=True, comment="Type of property")
    units_count = Column(Integer, nullable=True, comment="Number of units")
    amenities = Column(JSON, nullable=True, comment="Property amenities")
    features = Column(JSON, nullable=True, comment="Property features")
    website_url = Column(String(255), nullable=True, comment="Property website")
    hubspot_property_id = Column(String(100), nullable=True, comment="HubSpot property ID")
    
    # Audit timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), comment="When the property was created")
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="When the property was last updated")


class PropertyManager(Base):
    """
    PropertyManager Model - Represents staff who manage properties
    """
    __tablename__ = "property_manager"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to company
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id"), nullable=False, comment="ID of the company this manager works for")
    
    # Manager information
    first_name = Column(String(100), nullable=False, comment="Manager's first name")
    last_name = Column(String(100), nullable=False, comment="Manager's last name")
    email = Column(String(255), nullable=False, unique=True, comment="Manager's email address")
    phone = Column(String(20), nullable=False, unique=True, comment="Manager's phone number")
    role = Column(String(100), nullable=True, comment="Manager's role/title")
    access_level = Column(String(50), nullable=False, default='read', comment="Access level (read/write)")
    
    # Audit timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), comment="When the manager was created")
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="When the manager was last updated")


class PropertyManagerAssignment(Base):
    """
    PropertyManagerAssignment Model - Links managers to properties
    """
    __tablename__ = "property_manager_assignment"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    property_id = Column(UUID(as_uuid=True), ForeignKey("property.id"), nullable=False, comment="ID of the property")
    property_manager_id = Column(UUID(as_uuid=True), ForeignKey("property_manager.id"), nullable=False, comment="ID of the property manager")
    
    # Assignment details
    is_primary = Column(Boolean, default=False, comment="Whether this manager is the primary contact for the property")
    start_date = Column(Date, nullable=False, comment="When the assignment starts")
    end_date = Column(Date, nullable=True, comment="When the assignment ends (null if ongoing)")
    permissions = Column(JSON, nullable=True, comment="Specific permissions for this assignment")
    notification_preferences = Column(JSON, nullable=True, comment="How this manager wants to be notified")
    
    # Audit timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), comment="When the assignment was created")
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="When the assignment was last updated")


class Chatbot(Base):
    """
    Chatbot Model - Represents AI assistants deployed on property websites
    """
    __tablename__ = "chatbot"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key
    property_id = Column(UUID(as_uuid=True), ForeignKey("property.id"), nullable=False, comment="ID of the property this chatbot serves")
    
    # Chatbot configuration - matching database schema
    name = Column(String(100), nullable=False, comment="Name of the chatbot")
    avatar_url = Column(String(255), nullable=True, comment="Avatar URL")
    is_active = Column(Boolean, default=True, comment="Whether the chatbot is active")
    welcome_message = Column(Text, nullable=True, comment="Welcome message")
    embed_code = Column(Text, nullable=True, comment="Embed code")
    widget_settings = Column(JSON, nullable=True, comment="Widget settings")
    
    # Audit timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), comment="When the chatbot was created")
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="When the chatbot was last updated")


class FAQ(Base):
    """
    FAQ Model - Frequently asked questions for properties
    """
    __tablename__ = "faq"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key
    property_id = Column(UUID(as_uuid=True), ForeignKey("property.id"), nullable=False, comment="ID of the property this FAQ belongs to")
    
    # FAQ content
    question = Column(Text, nullable=False, comment="The question")
    answer = Column(Text, nullable=False, comment="The answer")
    category = Column(String(100), nullable=True, comment="FAQ category")
    source_type = Column(String(50), nullable=True, comment="Source type of the FAQ")
    
    # Audit timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), comment="When the FAQ was created")
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="When the FAQ was last updated")


class User(Base):
    """
    User Model - Represents potential tenants/leads
    """
    __tablename__ = "user"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User information - matching database schema
    first_name = Column(String(100), nullable=False, comment="User's first name")
    last_name = Column(String(100), nullable=False, comment="User's last name")
    email = Column(String(255), nullable=True, unique=True, comment="User's email address")
    phone = Column(String(20), nullable=True, unique=True, comment="User's phone number")
    age = Column(Integer, nullable=True, comment="User's age")
    lead_source = Column(String(100), nullable=True, comment="How the user found us")
    # Audit timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), comment="When the user was created")
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="When the user was last updated")


class Conversation(Base):
    """
    Conversation Model - Records interactions between users and chatbots
    IMPORTANT: This matches the ACTUAL database schema (NO HubSpot fields)
    """
    __tablename__ = "conversation"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    chatbot_id = Column(UUID(as_uuid=True), ForeignKey("chatbot.id"), nullable=False, comment="ID of the chatbot handling this conversation")
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True, comment="ID of the user in this conversation")
    
    # Conversation timing
    start_time = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), comment="When the conversation started")
    end_time = Column(DateTime(timezone=True), nullable=True, comment="When the conversation ended")
    
    # Lead qualification flags
    is_qualified = Column(Boolean, default=False, comment="Whether this lead has been qualified")
    is_book_tour = Column(Boolean, default=False, comment="Whether the user wants to book a tour")
    
    # Tour information
    tour_type = Column(String(50), nullable=True, comment="Type of tour requested")
    tour_datetime = Column(DateTime(timezone=False), nullable=True, comment="Requested tour date and time")
    
    # AI insights
    ai_intent_summary = Column(Text, nullable=True, comment="AI-generated summary of user's intent")
    
    # Apartment preferences
    apartment_size_preference = Column(String(50), nullable=True, comment="Preferred apartment size")
    move_in_date = Column(Date, nullable=True, comment="User's desired move-in date")
    
    # Budget information
    price_range_min = Column(DECIMAL(10,2), nullable=True, comment="Minimum budget for rent")
    price_range_max = Column(DECIMAL(10,2), nullable=True, comment="Maximum budget for rent")
    
    # Household information
    occupants_count = Column(Integer, nullable=True, comment="Number of occupants")
    has_pets = Column(Boolean, nullable=True, comment="Whether the user has pets")
    pet_details = Column(JSON, nullable=True, comment="Pet details")
    
    # Additional preferences
    desired_features = Column(JSON, nullable=True, comment="Desired apartment features")
    work_location = Column(String(255), nullable=True, comment="User's work location")
    reason_for_moving = Column(Text, nullable=True, comment="User's reason for moving")
    
    # Lead management
    pre_qualified = Column(Boolean, default=False, comment="Whether the user is pre-qualified")
    source = Column(String(100), nullable=True, comment="Source of this conversation")
    status = Column(String(50), nullable=True, comment="Current status of the lead")
    notification_status = Column(JSON, nullable=True, comment="Notification delivery status")
    lead_score = Column(Integer, nullable=True, comment="Calculated lead score")
    
    # NO HubSpot fields - they don't exist in the actual database!
    
    # Audit timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), comment="When the conversation was created")
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="When the conversation was last updated")


class Message(Base):
    """
    Message Model - Individual messages within conversations
    """
    __tablename__ = "message"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversation.id"), nullable=False, comment="ID of the conversation this message belongs to")
    
    # Message details
    sender_type = Column(String(20), nullable=False, comment="Who sent the message (user/bot)")
    message_text = Column(Text, nullable=False, comment="The message content")
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), comment="When the message was sent")
    message_type = Column(String(50), nullable=True, comment="Type of message")
    
    # FIXED: Use different Python attribute name but keep database column name
    message_metadata = Column("metadata", JSON, nullable=True, comment="Additional message metadata")
    
    # Audit timestamp
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), comment="When the message record was created")


class LeadNotification(Base):
    """
    LeadNotification Model - Tracks notifications sent to managers
    """
    __tablename__ = "lead_notification"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversation.id"), nullable=False, comment="ID of the conversation that triggered this notification")
    property_manager_id = Column(UUID(as_uuid=True), ForeignKey("property_manager.id"), nullable=True, comment="ID of the manager who should receive this notification")
    
    # Notification details
    notification_type = Column(String(50), nullable=True, comment="Type of notification")
    status = Column(String(50), nullable=True, comment="Status of the notification")
    sent_at = Column(DateTime(timezone=True), nullable=True, comment="When the notification was sent")
    read_at = Column(DateTime(timezone=True), nullable=True, comment="When the notification was read")
    response_at = Column(DateTime(timezone=True), nullable=True, comment="When the manager responded")
    
    # Audit timestamp
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), comment="When the notification record was created")


class WebsiteIntegration(Base):
    """
    WebsiteIntegration Model - Configuration for embedding chatbots on external websites
    """
    __tablename__ = "website_integration"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    property_id = Column(UUID(as_uuid=True), ForeignKey("property.id"), nullable=False, comment="ID of the property")
    chatbot_id = Column(UUID(as_uuid=True), ForeignKey("chatbot.id"), nullable=True, comment="ID of the chatbot")
    
    # Integration details
    website_url = Column(String(255), nullable=False, comment="URL of the website where the chatbot is embedded")
    integration_type = Column(String(50), nullable=True, comment="Type of integration")
    configuration = Column(JSON, nullable=True, comment="Integration configuration")
    is_active = Column(Boolean, default=True, comment="Whether the integration is active")
    tracking_id = Column(String(100), nullable=True, comment="Tracking ID for analytics")
    
    # Audit timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), comment="When the integration was created")
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="When the integration was last updated")