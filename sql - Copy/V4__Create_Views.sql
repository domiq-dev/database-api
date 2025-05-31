-- V4__Create_Views.sql
-- Creates database views for common queries
-- For multi-tenant property management chatbot database

-- Property manager properties view
-- Shows only properties a manager has access to
CREATE OR REPLACE VIEW property_manager_properties_view AS
SELECT 
    p.*,
    pma.is_primary,
    pma.permissions,
    pma.notification_preferences
FROM 
    property p
JOIN 
    property_manager_assignment pma ON p.id = pma.property_id
WHERE 
    pma.property_manager_id = current_setting('app.current_property_manager_id', true)::uuid
    AND (pma.end_date IS NULL OR pma.end_date >= CURRENT_DATE);

COMMENT ON VIEW property_manager_properties_view IS 'Shows only properties a manager has access to';

-- Property lead summary view
-- Summary of leads per property
CREATE OR REPLACE VIEW property_lead_summary_view AS
SELECT 
    p.id AS property_id,
    p.name AS property_name,
    COUNT(c.id) AS lead_count,
    SUM(CASE WHEN c.is_qualified THEN 1 ELSE 0 END) AS qualified_leads,
    SUM(CASE WHEN c.is_book_tour THEN 1 ELSE 0 END) AS tour_booked,
    SUM(CASE WHEN c.status = 'new' THEN 1 ELSE 0 END) AS new_leads,
    SUM(CASE WHEN c.status = 'contacted' THEN 1 ELSE 0 END) AS contacted_leads,
    SUM(CASE WHEN c.status = 'scheduled' THEN 1 ELSE 0 END) AS scheduled_leads,
    SUM(CASE WHEN c.status = 'converted' THEN 1 ELSE 0 END) AS converted_leads
FROM 
    property p
JOIN 
    chatbot cb ON p.id = cb.property_id
LEFT JOIN 
    conversation c ON cb.id = c.chatbot_id
WHERE 
    c.created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY 
    p.id, p.name;

COMMENT ON VIEW property_lead_summary_view IS 'Summary of leads per property for the last 30 days';

-- Manager leads view
-- Shows all leads for properties a manager is assigned to
CREATE OR REPLACE VIEW manager_leads_view AS
SELECT 
    c.*,
    p.name AS property_name,
    u.first_name,
    u.last_name,
    u.email,
    u.phone,
    u.hubspot_contact_id
FROM 
    conversation c
JOIN 
    chatbot cb ON c.chatbot_id = cb.id
JOIN 
    property p ON cb.property_id = p.id
JOIN 
    "user" u ON c.user_id = u.id
JOIN 
    property_manager_assignment pma ON p.id = pma.property_id
WHERE 
    pma.property_manager_id = current_setting('app.current_property_manager_id', true)::uuid
    AND (pma.end_date IS NULL OR pma.end_date >= CURRENT_DATE);

COMMENT ON VIEW manager_leads_view IS 'Shows all leads for properties a manager is assigned to';

-- Recent conversations view
-- Shows recent conversations with basic metrics
CREATE OR REPLACE VIEW recent_conversations_view AS
SELECT 
    c.id,
    c.start_time,
    c.end_time,
    c.is_qualified,
    c.is_book_tour,
    c.status,
    c.lead_score,
    p.name AS property_name,
    u.first_name,
    u.last_name,
    u.email,
    u.phone,
    COUNT(m.id) AS message_count,
    MAX(m.timestamp) AS last_message_time
FROM 
    conversation c
JOIN 
    chatbot cb ON c.chatbot_id = cb.id
JOIN 
    property p ON cb.property_id = p.id
JOIN 
    "user" u ON c.user_id = u.id
LEFT JOIN 
    message m ON c.id = m.conversation_id
WHERE 
    c.created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY 
    c.id, c.start_time, c.end_time, c.is_qualified, c.is_book_tour, 
    c.status, c.lead_score, p.name, u.first_name, u.last_name, u.email, u.phone
ORDER BY 
    c.start_time DESC;

COMMENT ON VIEW recent_conversations_view IS 'Shows recent conversations from the last 7 days with basic metrics';

-- Qualified leads view
-- Shows all qualified leads across properties
CREATE OR REPLACE VIEW qualified_leads_view AS
SELECT 
    c.id AS conversation_id,
    c.start_time,
    c.is_book_tour,
    c.tour_datetime,
    c.apartment_size_preference,
    c.move_in_date,
    c.price_range_min,
    c.price_range_max,
    c.lead_score,
    c.status,
    p.id AS property_id,
    p.name AS property_name,
    u.id AS user_id,
    u.first_name,
    u.last_name,
    u.email,
    u.phone
FROM 
    conversation c
JOIN 
    chatbot cb ON c.chatbot_id = cb.id
JOIN 
    property p ON cb.property_id = p.id
JOIN 
    "user" u ON c.user_id = u.id
WHERE 
    c.is_qualified = TRUE;

COMMENT ON VIEW qualified_leads_view IS 'Shows all qualified leads across properties';