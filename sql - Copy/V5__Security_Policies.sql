-- V5__Security_Policies.sql
-- Implements row-level security for multi-tenant isolation
-- For multi-tenant property management chatbot database

-- Create function to set current company context
CREATE OR REPLACE FUNCTION set_current_company_context(company_id uuid)
RETURNS void AS $$
BEGIN
  PERFORM set_config('app.current_company_id', company_id::text, false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION set_current_company_context IS 'Sets the current company context for row-level security policies';

-- Create function to set current property manager context
CREATE OR REPLACE FUNCTION set_current_property_manager_context(property_manager_id uuid)
RETURNS void AS $$
BEGIN
  PERFORM set_config('app.current_property_manager_id', property_manager_id::text, false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION set_current_property_manager_context IS 'Sets the current property manager context for row-level security policies';

-- Enable row-level security on company table
ALTER TABLE company ENABLE ROW LEVEL SECURITY;

-- Create policy for company table
CREATE POLICY company_isolation_policy ON company
    USING (id = current_setting('app.current_company_id', true)::uuid);

COMMENT ON POLICY company_isolation_policy ON company IS 'Ensures users can only see their own company';

-- Enable row-level security on property table
ALTER TABLE property ENABLE ROW LEVEL SECURITY;

-- Create policy for property table
CREATE POLICY property_isolation_policy ON property
    USING (company_id = current_setting('app.current_company_id', true)::uuid);

COMMENT ON POLICY property_isolation_policy ON property IS 'Ensures users can only see properties belonging to their company';

-- Enable row-level security on property_manager table
ALTER TABLE property_manager ENABLE ROW LEVEL SECURITY;

-- Create policy for property_manager table
CREATE POLICY property_manager_isolation_policy ON property_manager
    USING (company_id = current_setting('app.current_company_id', true)::uuid);

COMMENT ON POLICY property_manager_isolation_policy ON property_manager IS 'Ensures users can only see property managers belonging to their company';

-- Enable row-level security on property_manager_assignment table
ALTER TABLE property_manager_assignment ENABLE ROW LEVEL SECURITY;

-- Create policy for property_manager_assignment table
CREATE POLICY property_manager_assignment_isolation_policy ON property_manager_assignment
    USING (property_id IN (SELECT id FROM property WHERE company_id = current_setting('app.current_company_id', true)::uuid));

COMMENT ON POLICY property_manager_assignment_isolation_policy ON property_manager_assignment IS 'Ensures users can only see assignments for properties belonging to their company';

-- Create policy for property managers to see only their assignments
CREATE POLICY property_manager_own_assignments_policy ON property_manager_assignment
    USING (property_manager_id = current_setting('app.current_property_manager_id', true)::uuid);

COMMENT ON POLICY property_manager_own_assignments_policy ON property_manager_assignment IS 'Ensures property managers can only see their own assignments';

-- Enable row-level security on chatbot table
ALTER TABLE chatbot ENABLE ROW LEVEL SECURITY;

-- Create policy for chatbot table
CREATE POLICY chatbot_isolation_policy ON chatbot
    USING (property_id IN (SELECT id FROM property WHERE company_id = current_setting('app.current_company_id', true)::uuid));

COMMENT ON POLICY chatbot_isolation_policy ON chatbot IS 'Ensures users can only see chatbots for properties belonging to their company';

-- Enable row-level security on faq table
ALTER TABLE faq ENABLE ROW LEVEL SECURITY;

-- Create policy for faq table
CREATE POLICY faq_isolation_policy ON faq
    USING (property_id IN (SELECT id FROM property WHERE company_id = current_setting('app.current_company_id', true)::uuid));

COMMENT ON POLICY faq_isolation_policy ON faq IS 'Ensures users can only see FAQs for properties belonging to their company';

-- Enable row-level security on conversation table
ALTER TABLE conversation ENABLE ROW LEVEL SECURITY;

-- Create policy for conversation table
CREATE POLICY conversation_isolation_policy ON conversation
    USING (chatbot_id IN (
        SELECT c.id FROM chatbot c
        JOIN property p ON c.property_id = p.id
        WHERE p.company_id = current_setting('app.current_company_id', true)::uuid
    ));

COMMENT ON POLICY conversation_isolation_policy ON conversation IS 'Ensures users can only see conversations for chatbots belonging to their company';

-- Create policy for property managers to see only conversations for their properties
CREATE POLICY property_manager_conversation_policy ON conversation
    USING (chatbot_id IN (
        SELECT c.id FROM chatbot c
        JOIN property p ON c.property_id = p.id
        JOIN property_manager_assignment pma ON p.id = pma.property_id
        WHERE pma.property_manager_id = current_setting('app.current_property_manager_id', true)::uuid
        AND (pma.end_date IS NULL OR pma.end_date >= CURRENT_DATE)
    ));

COMMENT ON POLICY property_manager_conversation_policy ON conversation IS 'Ensures property managers can only see conversations for properties they are assigned to';

-- Enable row-level security on message table
ALTER TABLE message ENABLE ROW LEVEL SECURITY;

-- Create policy for message table
CREATE POLICY message_isolation_policy ON message
    USING (conversation_id IN (
        SELECT c.id FROM conversation c
        JOIN chatbot cb ON c.chatbot_id = cb.id
        JOIN property p ON cb.property_id = p.id
        WHERE p.company_id = current_setting('app.current_company_id', true)::uuid
    ));

COMMENT ON POLICY message_isolation_policy ON message IS 'Ensures users can only see messages for conversations belonging to their company';

-- Enable row-level security on lead_notification table
ALTER TABLE lead_notification ENABLE ROW LEVEL SECURITY;

-- Create policy for lead_notification table
CREATE POLICY lead_notification_isolation_policy ON lead_notification
    USING (conversation_id IN (
        SELECT c.id FROM conversation c
        JOIN chatbot cb ON c.chatbot_id = cb.id
        JOIN property p ON cb.property_id = p.id
        WHERE p.company_id = current_setting('app.current_company_id', true)::uuid
    ));

COMMENT ON POLICY lead_notification_isolation_policy ON lead_notification IS 'Ensures users can only see notifications for conversations belonging to their company';

-- Create policy for property managers to see only their notifications
CREATE POLICY property_manager_notification_policy ON lead_notification
    USING (property_manager_id = current_setting('app.current_property_manager_id', true)::uuid);

COMMENT ON POLICY property_manager_notification_policy ON lead_notification IS 'Ensures property managers can only see their own notifications';

-- Create application roles using DO blocks to check if they exist first
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_admin') THEN
        CREATE ROLE app_admin;
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_property_manager') THEN
        CREATE ROLE app_property_manager;
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_readonly') THEN
        CREATE ROLE app_readonly;
    END IF;
END
$$;

-- Grant permissions to roles
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_admin;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_admin;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app_admin;

GRANT SELECT, INSERT, UPDATE ON company, property, property_manager, property_manager_assignment, 
                               chatbot, faq, "user", conversation, message, 
                               lead_notification, website_integration TO app_property_manager;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO app_property_manager;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app_property_manager;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;
GRANT EXECUTE ON FUNCTION set_current_company_context, set_current_property_manager_context TO app_readonly;
