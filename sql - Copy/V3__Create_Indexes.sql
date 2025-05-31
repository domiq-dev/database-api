-- V3__Create_Indexes.sql
-- Creates indexes for performance optimization
-- For multi-tenant property management chatbot database

-- Property indexes
CREATE INDEX idx_property_company ON property(company_id);

-- Property manager indexes
CREATE INDEX idx_property_manager_company ON property_manager(company_id);

-- Property manager assignment indexes
CREATE INDEX idx_property_manager_assignment_property ON property_manager_assignment(property_id);
CREATE INDEX idx_property_manager_assignment_manager ON property_manager_assignment(property_manager_id);

-- Chatbot indexes
CREATE INDEX idx_chatbot_property ON chatbot(property_id);

-- FAQ indexes
CREATE INDEX idx_faq_property ON faq(property_id);

-- Conversation indexes
CREATE INDEX idx_conversation_chatbot ON conversation(chatbot_id);
CREATE INDEX idx_conversation_user ON conversation(user_id);
CREATE INDEX idx_conversation_status ON conversation(status);
CREATE INDEX idx_conversation_qualified ON conversation(is_qualified);
CREATE INDEX idx_conversation_book_tour ON conversation(is_book_tour);

-- Message indexes
CREATE INDEX idx_message_conversation ON message(conversation_id);
CREATE INDEX idx_message_timestamp ON message(timestamp);

-- Comment out vector embedding indexes since table doesn't exist yet
-- Vector embedding indexes
-- CREATE INDEX idx_vector_embedding_source ON vector_embedding(source_id, source_type);

-- Lead notification indexes
CREATE INDEX idx_lead_notification_conversation ON lead_notification(conversation_id);
CREATE INDEX idx_lead_notification_manager ON lead_notification(property_manager_id);
CREATE INDEX idx_lead_notification_status ON lead_notification(status);

-- Website integration indexes
CREATE INDEX idx_website_integration_property ON website_integration(property_id);
CREATE INDEX idx_website_integration_chatbot ON website_integration(chatbot_id);

