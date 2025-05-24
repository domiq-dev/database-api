from sqlalchemy import Date,Column, String, Float, Integer, DateTime, Boolean, ForeignKey, Text, JSON, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime, timezone

Base = declarative_base()


class User(Base):
    __tablename__ = "user"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255), unique=True)
    phone = Column(String(20))
    age = Column(Integer)
    lead_source = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Chatbot(Base):
    __tablename__ = "chatbot"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(UUID(as_uuid=True))
    name = Column(String(100), nullable=False)
    avatar_url = Column(String(255))
    is_active = Column(Boolean, default=True)
    welcome_message = Column(Text)
    embed_code = Column(Text)
    widget_settings = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Conversation(Base):
    __tablename__ = "conversation"
    __table_args__ = {'extend_existing': True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_id = Column(UUID(as_uuid=True), ForeignKey("chatbot.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"))
    is_qualified = Column(Boolean, default=False)
    is_book_tour = Column(Boolean, default=False)
    tour_type = Column(String, nullable=True)
    tour_datetime = Column(DateTime(timezone=False), nullable=True)  # Changed to timezone=False
    ai_intent_summary = Column(String, nullable=True)
    apartment_size_preference = Column(String, nullable=True)
    move_in_date = Column(Date, nullable=True)  # Changed to timezone=False
    price_range_min = Column(Float, nullable=True)
    price_range_max = Column(Float, nullable=True)
    occupants_count = Column(Integer, nullable=True)
    has_pets = Column(Boolean, nullable=True)
    pet_details = Column(JSON, nullable=True)
    desired_features = Column(JSON, nullable=True)
    work_location = Column(String, nullable=True)
    reason_for_moving = Column(String, nullable=True)
    pre_qualified = Column(Boolean, default=False)
    source = Column(String, nullable=True)
    status = Column(String, default="new")
    notification_status = Column(JSON, default={})
    lead_score = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))