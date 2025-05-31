-- V7__Database_Triggers.sql
-- Creates database triggers for automated actions

-- Create timestamp update function
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create timestamp triggers for all tables with updated_at column
CREATE TRIGGER company_timestamp_trigger
BEFORE UPDATE ON company
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER property_timestamp_trigger
BEFORE UPDATE ON property
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER property_manager_timestamp_trigger
BEFORE UPDATE ON property_manager
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER property_manager_assignment_timestamp_trigger
BEFORE UPDATE ON property_manager_assignment
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER chatbot_timestamp_trigger
BEFORE UPDATE ON chatbot
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER faq_timestamp_trigger
BEFORE UPDATE ON faq
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER user_timestamp_trigger
BEFORE UPDATE ON "user"
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER conversation_timestamp_trigger
BEFORE UPDATE ON conversation
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER message_timestamp_trigger
BEFORE UPDATE ON message
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Fix the trigger that references vector_embedding table
-- Comment out or remove this trigger since the table doesn't exist yet

-- CREATE TRIGGER vector_embedding_timestamp_trigger
-- BEFORE UPDATE ON vector_embedding
-- FOR EACH ROW
-- EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER lead_notification_timestamp_trigger
BEFORE UPDATE ON lead_notification
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER website_integration_timestamp_trigger
BEFORE UPDATE ON website_integration
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

-- Create function to update conversation status based on lead qualification
CREATE OR REPLACE FUNCTION update_conversation_status()
RETURNS TRIGGER AS $$
BEGIN
    -- If pre_qualified is set to true, update status to 'qualified'
    IF NEW.pre_qualified = TRUE AND (OLD.pre_qualified IS NULL OR OLD.pre_qualified = FALSE) THEN
        NEW.status = 'qualified';
    END IF;
    
    -- If tour is booked, update status to 'tour_scheduled'
    IF NEW.is_book_tour = TRUE AND (OLD.is_book_tour IS NULL OR OLD.is_book_tour = FALSE) THEN
        NEW.status = 'tour_scheduled';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for conversation status updates
CREATE TRIGGER conversation_status_trigger
BEFORE UPDATE ON conversation
FOR EACH ROW
EXECUTE FUNCTION update_conversation_status();

-- Create function to notify property managers of new leads
CREATE OR REPLACE FUNCTION create_lead_notification()
RETURNS TRIGGER AS $$
BEGIN
    -- If conversation status changed to 'qualified', create notification
    IF NEW.status = 'qualified' AND (OLD.status IS NULL OR OLD.status != 'qualified') THEN
        INSERT INTO lead_notification (
            conversation_id,
            notification_type,
            status
        )
        VALUES (
            NEW.id,
            'new_qualified_lead',
            'pending'
        );
    END IF;
    
    -- If conversation status changed to 'tour_scheduled', create notification
    IF NEW.status = 'tour_scheduled' AND (OLD.status IS NULL OR OLD.status != 'tour_scheduled') THEN
        INSERT INTO lead_notification (
            conversation_id,
            notification_type,
            status
        )
        VALUES (
            NEW.id,
            'tour_scheduled',
            'pending'
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for lead notifications
CREATE TRIGGER lead_notification_trigger
AFTER UPDATE ON conversation
FOR EACH ROW
EXECUTE FUNCTION create_lead_notification();

-- Create function to update vector embeddings when FAQ content changes
CREATE OR REPLACE FUNCTION update_faq_vector_embedding()
RETURNS TRIGGER AS $$
BEGIN
    -- Mark the vector embedding as needing update
    -- The actual vector calculation would be done by the application
    IF NEW.question != OLD.question OR NEW.answer != OLD.answer THEN
        -- Just log the change instead of updating a column that might not exist
        RAISE NOTICE 'Vector embedding for FAQ % needs update', NEW.id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Also comment out this trigger since vector_embedding_id column doesn't exist
-- CREATE TRIGGER faq_vector_embedding_trigger
-- AFTER UPDATE ON faq
-- FOR EACH ROW
-- WHEN (NEW.vector_embedding_id IS NOT NULL)
-- EXECUTE FUNCTION update_faq_vector_embedding();