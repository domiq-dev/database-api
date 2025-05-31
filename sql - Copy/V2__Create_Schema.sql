-- V2__Create_Schema.sql
-- Creates all core database tables for multi-tenant property management chatbot database
-- Optimized for POC with single apartment complex from one company

-- Create company table
CREATE TABLE company (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
	--Company name need to be unique
    logo_url VARCHAR(255),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(20),
    hubspot_company_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
	--With Timezone
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE company IS 'Core company entity – the parent organization that owns properties';
COMMENT ON COLUMN company.hubspot_company_id IS 'HubSpot company ID for integration';

-- Create property table
CREATE TABLE property (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES company(id) ON DELETE CASCADE ,
	--Ensures that when a company is removed, all its properties are automatically deleted; 
	-- If we want to keep it and make it null code is DELETE SET NULL
    name VARCHAR(255) NOT NULL,
    address VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    zip_code VARCHAR(20) NOT NULL,
    property_type VARCHAR(50),
    units_count INTEGER,
    amenities JSONB,
    features JSONB,
    website_url VARCHAR(255),
    hubspot_property_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE property IS 'Properties owned by a company (apartments, condos, etc.). Each property has one embedded chatbot';
COMMENT ON COLUMN property.hubspot_property_id IS 'HubSpot property ID for integration';

-- Create property_manager table
CREATE TABLE property_manager (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES company(id) ON DELETE CASCADE,
	-- if a company is dropped, its managers stay in the system but lose that link.
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL UNIQUE,
    role VARCHAR(100),
    access_level VARCHAR(50) NOT NULL DEFAULT 'read'
							CHECK (access_level IN ('write','read')),
							--preventing typos or invalid levels
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE property_manager IS 'Staff members who manage specific properties and receive leads';

-- Create property_manager_assignment table
CREATE TABLE property_manager_assignment (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID REFERENCES property(id) ON DELETE CASCADE,
    property_manager_id UUID REFERENCES property_manager(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE,
    start_date DATE NOT NULL,
    end_date DATE,
    permissions JSONB,
    notification_preferences JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
	CONSTRAINT chk_assignment_dates 
    CHECK (end_date IS NULL OR end_date >= start_date)
);

COMMENT ON TABLE property_manager_assignment IS 'Many-to-many relationship between properties and managers, with per-assignment permissions';

-- Create chatbot table
CREATE TABLE chatbot (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID REFERENCES property(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    avatar_url VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    welcome_message TEXT,
    embed_code TEXT,
    widget_settings JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
	-- one chatbot per property
	CONSTRAINT uq_chatbot_property UNIQUE (property_id) 
);

COMMENT ON TABLE chatbot IS 'Virtual assistant embedded on property websites';

-- Create faq table
CREATE TABLE faq (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID REFERENCES property(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(100),
    source_type VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE faq IS 'Frequently asked questions for each property, used by RAG';

-- Create user table
CREATE TABLE "user" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20) UNIQUE,
    age INTEGER CHECK (age >= 0),
    lead_source VARCHAR(100),
    hubspot_contact_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE "user" IS 'Potential tenants/leads interacting with chatbots';

-- Create conversation table
CREATE TABLE conversation (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_id UUID REFERENCES chatbot(id) ON DELETE CASCADE,
    user_id UUID REFERENCES "user"(id) ON DELETE SET NULL,
    start_time TIMESTAMPTZ DEFAULT NOW(),
    end_time TIMESTAMPTZ,
	CONSTRAINT chk_end_after_start  
  		CHECK (end_time IS NULL OR end_time > start_time),
    is_qualified BOOLEAN DEFAULT FALSE,
    is_book_tour BOOLEAN DEFAULT FALSE,
    tour_type VARCHAR(50),
    tour_datetime TIMESTAMP,
    ai_intent_summary TEXT,
    apartment_size_preference VARCHAR(50),
    move_in_date DATE,
    price_range_min DECIMAL(10,2) CHECK (price_range_min >= 0),
    price_range_max DECIMAL(10,2) CHECK (price_range_max >= price_range_min),
    occupants_count INTEGER CHECK (occupants_count >= 0),
    has_pets BOOLEAN,
    pet_details JSONB,
    desired_features JSONB,
    work_location VARCHAR(255),
    reason_for_moving TEXT,
    pre_qualified BOOLEAN DEFAULT FALSE,
    source VARCHAR(100),
    status VARCHAR(50),
    notification_status JSONB,
    lead_score INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE conversation IS 'Chat sessions between users and chatbots, including lead qualification data';

-- Create message table
CREATE TABLE message (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversation(id) ON DELETE CASCADE,
    sender_type VARCHAR(20) NOT NULL CHECK (sender_type IN ('user','bot')),
    message_text TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    message_type VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE message IS 'Individual messages in a conversation';

-- Create lead_notification table
CREATE TABLE lead_notification (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversation(id) ON DELETE CASCADE,
    property_manager_id UUID REFERENCES property_manager(id),
    notification_type VARCHAR(50),
    status VARCHAR(50),
    sent_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    response_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE lead_notification IS 'Tracks notifications sent to managers about new leads';

-- Create website_integration table
CREATE TABLE website_integration (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_id UUID REFERENCES property(id) ON DELETE CASCADE,
    website_url VARCHAR(255) NOT NULL,
    chatbot_id UUID REFERENCES chatbot(id),
    integration_type VARCHAR(50),
    configuration JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    tracking_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE website_integration IS 'Configuration for embedding chatbots on external property websites';