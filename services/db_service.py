import uuid
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from config.database import execute_query, fetch_one

# Set up logging
logger = logging.getLogger(__name__)

class DatabaseService:
    """Service class for database operations related to conversations and FAQs"""
    
    @staticmethod
    async def save_conversation(
        conversation_id: str,
        ai_intent_summary: str,
        is_qualified: bool,
        source: str = "LLM",
        status: str = "completed",
        chatbot_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Save conversation data to the database
        
        Args:
            conversation_id: Unique identifier for the conversation (from chatbot)
            ai_intent_summary: AI-generated summary of the conversation
            is_qualified: Whether the user was qualified during the conversation
            source: Source of the conversation (default: "LLM")
            status: Status of the conversation (default: "completed")
            chatbot_id: Optional chatbot ID (if available)
            user_id: Optional user ID (if available)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Generate UUID for the conversation record
            db_conversation_id = str(uuid.uuid4())
            
            query = """
                INSERT INTO conversation (
                    id, 
                    ai_intent_summary, 
                    is_qualified, 
                    source, 
                    status,
                    chatbot_id,
                    user_id,
                    start_time,
                    created_at,
                    updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """
            
            now = datetime.utcnow()
            
            result = await execute_query(
                query,
                db_conversation_id,
                ai_intent_summary,
                is_qualified,
                source,
                status,
                chatbot_id,
                user_id,
                now,  # start_time
                now,  # created_at
                now   # updated_at
            )
            
            if result:
                logger.info(f"Successfully saved conversation {conversation_id} to database with ID {db_conversation_id}")
                return True
            else:
                logger.error(f"Failed to save conversation {conversation_id} to database")
                return False
                
        except Exception as e:
            logger.error(f"Error saving conversation {conversation_id}: {str(e)}")
            return False
    
    @staticmethod
    async def save_unanswered_question(
        question: str,
        conversation_id: str,
        chatbot_id: Optional[str] = None,
        source: str = "chatbot_fallback"
    ) -> bool:
        """
        Save an unanswered question to a custom table for tracking knowledge gaps
        
        Since the FAQ table is for property-specific Q&As, we'll create a simple
        tracking mechanism for unanswered questions that need attention.
        
        Args:
            question: The unanswered question
            conversation_id: ID of the conversation where the question was asked
            chatbot_id: Optional chatbot ID
            source: Source of the question (default: "chatbot_fallback")
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # For now, we'll use a simple approach - create a message-like record
            # that can be queried later for unanswered questions
            query = """
                INSERT INTO message (
                    id,
                    conversation_id,
                    sender_type,
                    message_text,
                    message_type,
                    metadata,
                    timestamp,
                    created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """
            
            # We'll need to find the conversation ID in the database first
            conversation_query = """
                SELECT id FROM conversation 
                WHERE ai_intent_summary LIKE $1 OR status = 'completed'
                ORDER BY created_at DESC LIMIT 1
            """
            
            # Get the most recent conversation (this is a simplified approach)
            db_conversation = await fetch_one(conversation_query, f"%{conversation_id}%")
            
            if not db_conversation:
                logger.warning(f"Could not find database conversation for {conversation_id}, skipping unanswered question")
                return True  # Don't fail the whole operation
            
            message_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            metadata = {
                "original_conversation_id": conversation_id,
                "chatbot_id": chatbot_id,
                "source": source,
                "unanswered": True,
                "needs_attention": True
            }
            
            result = await execute_query(
                query,
                message_id,
                db_conversation["id"],
                "bot",  # sender_type
                question,
                "unanswered_question",  # message_type
                json.dumps(metadata),  # Convert metadata dict to JSON string
                now,  # timestamp
                now   # created_at
            )
            
            if result:
                logger.info(f"Successfully saved unanswered question for conversation {conversation_id}")
                return True
            else:
                logger.error(f"Failed to save unanswered question for conversation {conversation_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving unanswered question for conversation {conversation_id}: {str(e)}")
            return False
    
    @staticmethod
    async def update_conversation_status(
        ai_intent_summary: str,
        status: str,
        is_qualified: Optional[bool] = None
    ) -> bool:
        """
        Update the status of an existing conversation by finding it via AI intent summary
        
        Args:
            ai_intent_summary: AI intent summary to find the conversation
            status: New status for the conversation
            is_qualified: Optional qualification status update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if is_qualified is not None:
                query = """
                    UPDATE conversation 
                    SET status = $1, is_qualified = $2, updated_at = $3
                    WHERE ai_intent_summary = $4
                """
                result = await execute_query(
                    query,
                    status,
                    is_qualified,
                    datetime.utcnow(),
                    ai_intent_summary
                )
            else:
                query = """
                    UPDATE conversation 
                    SET status = $1, updated_at = $2
                    WHERE ai_intent_summary = $3
                """
                result = await execute_query(
                    query,
                    status,
                    datetime.utcnow(),
                    ai_intent_summary
                )
            
            if result:
                logger.info(f"Successfully updated conversation status to {status}")
                return True
            else:
                logger.error(f"Failed to update conversation status")
                return False
                
        except Exception as e:
            logger.error(f"Error updating conversation status: {str(e)}")
            return False
    
    @staticmethod
    async def get_conversation_by_summary(ai_intent_summary: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve conversation data from the database by AI intent summary
        
        Args:
            ai_intent_summary: AI intent summary to search for
            
        Returns:
            Dict containing conversation data if found, None otherwise
        """
        try:
            query = """
                SELECT 
                    id,
                    ai_intent_summary,
                    is_qualified,
                    source,
                    status,
                    chatbot_id,
                    user_id,
                    start_time,
                    created_at,
                    updated_at
                FROM conversation 
                WHERE ai_intent_summary = $1
                ORDER BY created_at DESC
                LIMIT 1
            """
            
            result = await fetch_one(query, ai_intent_summary)
            
            if result:
                return {
                    "id": result["id"],
                    "ai_intent_summary": result["ai_intent_summary"],
                    "is_qualified": result["is_qualified"],
                    "source": result["source"],
                    "status": result["status"],
                    "chatbot_id": result["chatbot_id"],
                    "user_id": result["user_id"],
                    "start_time": result["start_time"],
                    "created_at": result["created_at"],
                    "updated_at": result["updated_at"]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving conversation: {str(e)}")
            return None
    
    @staticmethod
    async def save_conversation_with_unanswered_question(
        conversation_id: str,
        ai_intent_summary: str,
        is_qualified: bool,
        kb_pending: Optional[str] = None,
        source: str = "LLM",
        status: str = "completed",
        chatbot_id: Optional[str] = None
    ) -> bool:
        """
        Save conversation data and optionally an unanswered question in a single operation
        
        Args:
            conversation_id: Unique identifier for the conversation
            ai_intent_summary: AI-generated summary of the conversation
            is_qualified: Whether the user was qualified during the conversation
            kb_pending: Optional unanswered question that triggered fallback
            source: Source of the conversation (default: "LLM")
            status: Status of the conversation (default: "completed")
            chatbot_id: Optional chatbot ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Save the conversation
            conversation_saved = await DatabaseService.save_conversation(
                conversation_id=conversation_id,
                ai_intent_summary=ai_intent_summary,
                is_qualified=is_qualified,
                source=source,
                status=status,
                chatbot_id=chatbot_id
            )
            
            # Save unanswered question if it exists
            question_saved = True  # Default to True if no question to save
            if kb_pending and kb_pending.strip():
                question_saved = await DatabaseService.save_unanswered_question(
                    question=kb_pending,
                    conversation_id=conversation_id,
                    chatbot_id=chatbot_id
                )
            
            success = conversation_saved and question_saved
            
            if success:
                logger.info(f"Successfully saved all data for conversation {conversation_id}")
            else:
                logger.error(f"Partial failure saving data for conversation {conversation_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error saving conversation and question data for {conversation_id}: {str(e)}")
            return False
    
    @staticmethod
    async def get_unanswered_questions(limit: int = 50) -> list:
        """
        Retrieve recent unanswered questions that need attention
        
        Args:
            limit: Maximum number of questions to retrieve
            
        Returns:
            List of unanswered questions with metadata
        """
        try:
            query = """
                SELECT 
                    m.message_text as question,
                    m.timestamp,
                    m.metadata,
                    c.ai_intent_summary,
                    c.is_qualified
                FROM message m
                JOIN conversation c ON m.conversation_id = c.id
                WHERE m.message_type = 'unanswered_question'
                ORDER BY m.timestamp DESC
                LIMIT $1
            """
            
            # Note: This would need a different implementation if fetch_multiple is not available
            # For now, we'll use fetch_one in a loop or implement fetch_multiple
            result = await fetch_one(query, limit)
            
            if result:
                return [result]  # Return as list for consistency
            return []
            
        except Exception as e:
            logger.error(f"Error retrieving unanswered questions: {str(e)}")
            return []

# Create a singleton instance for easy importing
db_service = DatabaseService() 