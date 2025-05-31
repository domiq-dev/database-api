-- V6__Stored_Procedures.sql
-- Creates stored procedures and functions
-- For multi-tenant property management chatbot database

-- Procedure for assigning property managers to properties
CREATE OR REPLACE PROCEDURE assign_property_manager(
    p_property_id UUID,
    p_property_manager_id UUID,
    p_is_primary BOOLEAN DEFAULT FALSE,
    p_start_date DATE DEFAULT CURRENT_DATE,
    p_end_date DATE DEFAULT NULL,
    p_permissions JSONB DEFAULT NULL,
    p_notification_preferences JSONB DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_company_id UUID;
    v_manager_company_id UUID;
BEGIN
    -- Get the company ID for the property
    SELECT company_id INTO v_company_id
    FROM property
    WHERE id = p_property_id;
    
    -- Get the company ID for the property manager
    SELECT company_id INTO v_manager_company_id
    FROM property_manager
    WHERE id = p_property_manager_id;
    
    -- Verify that property and manager belong to the same company
    IF v_company_id != v_manager_company_id THEN
        RAISE EXCEPTION 'Property and property manager must belong to the same company';
    END IF;
    
    -- If setting as primary, unset any existing primary managers for this property
    IF p_is_primary THEN
        UPDATE property_manager_assignment
        SET is_primary = FALSE
        WHERE property_id = p_property_id
        AND is_primary = TRUE
        AND (end_date IS NULL OR end_date >= CURRENT_DATE);
    END IF;
    
    -- Check if assignment already exists
    IF EXISTS (
        SELECT 1 FROM property_manager_assignment
        WHERE property_id = p_property_id
        AND property_manager_id = p_property_manager_id
        AND (end_date IS NULL OR end_date >= CURRENT_DATE)
    ) THEN
        -- Update existing assignment
        UPDATE property_manager_assignment
        SET is_primary = p_is_primary,
            start_date = p_start_date,
            end_date = p_end_date,
            permissions = COALESCE(p_permissions, permissions),
            notification_preferences = COALESCE(p_notification_preferences, notification_preferences),
            updated_at = NOW()
        WHERE property_id = p_property_id
        AND property_manager_id = p_property_manager_id
        AND (end_date IS NULL OR end_date >= CURRENT_DATE);
    ELSE
        -- Create new assignment
        INSERT INTO property_manager_assignment (
            property_id,
            property_manager_id,
            is_primary,
            start_date,
            end_date,
            permissions,
            notification_preferences
        ) VALUES (
            p_property_id,
            p_property_manager_id,
            p_is_primary,
            p_start_date,
            p_end_date,
            p_permissions,
            p_notification_preferences
        );
    END IF;
END;
$$;

COMMENT ON PROCEDURE assign_property_manager IS 'Assigns a property manager to a property, handling primary status and existing assignments';

-- Procedure for updating lead qualification status
CREATE OR REPLACE PROCEDURE update_lead_qualification_status(
    p_conversation_id UUID,
    p_is_qualified BOOLEAN,
    p_lead_score INTEGER DEFAULT NULL,
    p_status VARCHAR(50) DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE conversation
    SET 
        is_qualified = p_is_qualified,
        lead_score = COALESCE(p_lead_score, lead_score),
        status = COALESCE(p_status, status),
        updated_at = NOW()
    WHERE id = p_conversation_id;
    
    -- Create notifications for property managers if lead is qualified
    IF p_is_qualified THEN
        INSERT INTO lead_notification (
            conversation_id,
            property_manager_id,
            notification_type,
            status,
            sent_at
        )
        SELECT 
            p_conversation_id,
            pma.property_manager_id,
            'email',
            'sent',
            NOW()
        FROM 
            conversation c
        JOIN 
            chatbot cb ON c.chatbot_id = cb.id
        JOIN 
            property_manager_assignment pma ON cb.property_id = pma.property_id
        WHERE 
            c.id = p_conversation_id
            AND (pma.end_date IS NULL OR pma.end_date >= CURRENT_DATE)
            AND NOT EXISTS (
                SELECT 1 FROM lead_notification ln 
                WHERE ln.conversation_id = p_conversation_id 
                AND ln.property_manager_id = pma.property_manager_id
            );
    END IF;
END;
$$;

COMMENT ON PROCEDURE update_lead_qualification_status IS 'Updates the qualification status of a lead and creates notifications for property managers';

-- Function to calculate lead score based on conversation data
CREATE OR REPLACE FUNCTION calculate_lead_score(p_conversation_id UUID)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_score INTEGER := 0;
    v_conversation conversation%ROWTYPE;
BEGIN
    -- Get conversation data
    SELECT * INTO v_conversation
    FROM conversation
    WHERE id = p_conversation_id;
    
    -- Base score for all leads
    v_score := 10;
    
    -- Add points for qualification
    IF v_conversation.is_qualified THEN
        v_score := v_score + 30;
    END IF;
    
    -- Add points for booking a tour
    IF v_conversation.is_book_tour THEN
        v_score := v_score + 40;
    END IF;
    
    -- Add points for having move-in date
    IF v_conversation.move_in_date IS NOT NULL THEN
        -- More points for near-term move-in dates
        IF v_conversation.move_in_date <= CURRENT_DATE + INTERVAL '30 days' THEN
            v_score := v_score + 20;
        ELSIF v_conversation.move_in_date <= CURRENT_DATE + INTERVAL '90 days' THEN
            v_score := v_score + 10;
        ELSE
            v_score := v_score + 5;
        END IF;
    END IF;
    
    -- Add points for price range matching
    IF v_conversation.price_range_min IS NOT NULL AND v_conversation.price_range_max IS NOT NULL THEN
        v_score := v_score + 10;
    END IF;
    
    -- Add points for providing contact information
    SELECT 
        CASE 
            WHEN u.email IS NOT NULL AND u.phone IS NOT NULL THEN v_score + 15
            WHEN u.email IS NOT NULL OR u.phone IS NOT NULL THEN v_score + 10
            ELSE v_score
        END INTO v_score
    FROM "user" u
    JOIN conversation c ON u.id = c.user_id
    WHERE c.id = p_conversation_id;
    
    -- Cap score at 100
    IF v_score > 100 THEN
        v_score := 100;
    END IF;
    
    -- Update the conversation with the calculated score
    UPDATE conversation
    SET lead_score = v_score,
        updated_at = NOW()
    WHERE id = p_conversation_id;
    
    RETURN v_score;
END;
$$;

COMMENT ON FUNCTION calculate_lead_score IS 'Calculates a lead score (0-100) based on conversation data and updates the conversation record';

-- Function to get property managers for a specific property
CREATE OR REPLACE FUNCTION get_property_managers(p_property_id UUID)
RETURNS TABLE (
    manager_id UUID,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(20),
    role VARCHAR(100),
    is_primary BOOLEAN,
    permissions JSONB,
    notification_preferences JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pm.id AS manager_id,
        pm.first_name,
        pm.last_name,
        pm.email,
        pm.phone,
        pm.role,
        pma.is_primary,
        pma.permissions,
        pma.notification_preferences
    FROM 
        property_manager pm
    JOIN 
        property_manager_assignment pma ON pm.id = pma.property_manager_id
    WHERE 
        pma.property_id = p_property_id
        AND (pma.end_date IS NULL OR pma.end_date >= CURRENT_DATE)
    ORDER BY 
        pma.is_primary DESC,
        pm.last_name,
        pm.first_name;
END;
$$;

COMMENT ON FUNCTION get_property_managers IS 'Returns all property managers assigned to a specific property';

-- Procedure for tracking notification status
CREATE OR REPLACE PROCEDURE update_notification_status(
    p_notification_id UUID,
    p_status VARCHAR(50),
    p_read_at TIMESTAMP DEFAULT NULL,
    p_response_at TIMESTAMP DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE lead_notification
    SET 
        status = p_status,
        read_at = COALESCE(p_read_at, read_at),
        response_at = COALESCE(p_response_at, response_at)
    WHERE id = p_notification_id;
END;
$$;

COMMENT ON PROCEDURE update_notification_status IS 'Updates the status of a lead notification';

-- Add procedure to create property with chatbot
CREATE OR REPLACE PROCEDURE create_property_with_chatbot(
    p_company_id UUID,
    p_name VARCHAR(255),
    p_address VARCHAR(255),
    p_city VARCHAR(100),
    p_state VARCHAR(50),
    p_zip_code VARCHAR(20),
    OUT p_property_id UUID,
    OUT p_chatbot_id UUID
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Create property
    INSERT INTO property (
        company_id, name, address, city, state, zip_code
    ) VALUES (
        p_company_id, p_name, p_address, p_city, p_state, p_zip_code
    ) RETURNING id INTO p_property_id;
    
    -- Auto-create chatbot for this property
    INSERT INTO chatbot (
        property_id,
        name,
        welcome_message,
        is_active
    ) VALUES (
        p_property_id,
        p_name || ' Assistant',
        'Welcome to ' || p_name || '! How can I help you today?',
        TRUE
    ) RETURNING id INTO p_chatbot_id;
    
END;
$$;
