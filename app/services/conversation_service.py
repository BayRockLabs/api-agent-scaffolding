"""
Conversation management service.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
import structlog

from app.core.auth import UserContext
from app.core.exceptions import NotFoundException, ValidationException
from app.infrastructure.snowflake.engine import snowflake_engine

logger = structlog.get_logger()


class ConversationService:
    """
    Manages conversation history and metadata.
    
    Conversations are stored in Snowflake for:
    - Long-term persistence
    - Analytics and reporting
    - Audit trail
    
    Note: Agent checkpoints are stored separately (Redis/Postgres/Memory)
    """
    
    def __init__(self):
        self.engine = snowflake_engine
    
    async def create_conversation(
        self,
        user_context: UserContext,
        initial_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new conversation.
        
        Args:
            user_context: User context for ownership
            initial_message: Optional first message
            metadata: Additional metadata
            
        Returns:
            Conversation dict with conversation_id
        """
        conversation_id = str(uuid.uuid4())
        
        # Insert conversation record
        query = """
            INSERT INTO conversations (
                conversation_id,
                user_id,
                user_email,
                created_at,
                updated_at,
                metadata
            ) VALUES (
                :conversation_id,
                :user_id,
                :user_email,
                CURRENT_TIMESTAMP(),
                CURRENT_TIMESTAMP(),
                PARSE_JSON(:metadata)
            )
        """
        
        self.engine.execute_query(
            query,
            {
                "conversation_id": conversation_id,
                "user_id": user_context.user_id,
                "user_email": user_context.email,
                "metadata": json.dumps(metadata or {}),
            }
        )
        
        # Add initial message if provided
        if initial_message:
            await self.add_message(
                conversation_id=conversation_id,
                user_context=user_context,
                role="user",
                content=initial_message,
            )
        
        logger.info(
            "Conversation created",
            conversation_id=conversation_id,
            user_id=user_context.user_id,
        )
        
        return {
            "conversation_id": conversation_id,
            "user_id": user_context.user_id,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
    
    async def get_conversation(
        self,
        conversation_id: str,
        user_context: UserContext,
    ) -> Optional[Dict[str, Any]]:
        """
        Get conversation by ID with user scoping.
        
        Args:
            conversation_id: Conversation identifier
            user_context: User context for validation
            
        Returns:
            Conversation dict with messages or None
            
        Raises:
            NotFoundException: If conversation not found or not owned by user
        """
        # Get conversation metadata
        query = """
            SELECT 
                conversation_id,
                user_id,
                user_email,
                created_at,
                updated_at,
                metadata
            FROM conversations
            WHERE conversation_id = :conversation_id
                AND user_id = :user_id
        """
        
        result = self.engine.execute_query_one(
            query,
            {
                "conversation_id": conversation_id,
                "user_id": user_context.user_id,
            }
        )
        
        if not result:
            raise NotFoundException(
                f"Conversation {conversation_id} not found",
                details={"conversation_id": conversation_id}
            )
        
        # Get messages
        messages = await self.get_messages(conversation_id, user_context)
        
        return {
            "conversation_id": result["CONVERSATION_ID"],
            "user_id": result["USER_ID"],
            "created_at": result["CREATED_AT"].isoformat() if result["CREATED_AT"] else None,
            "updated_at": result["UPDATED_AT"].isoformat() if result["UPDATED_AT"] else None,
            "metadata": json.loads(result["METADATA"]) if result["METADATA"] else {},
            "messages": messages,
        }
    
    async def list_conversations(
        self,
        user_context: UserContext,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List conversations for a user.
        
        Args:
            user_context: User context
            limit: Maximum conversations to return
            offset: Pagination offset
            
        Returns:
            List of conversation summaries
        """
        query = """
            SELECT 
                c.conversation_id,
                c.created_at,
                c.updated_at,
                c.metadata,
                COUNT(m.id) as message_count,
                MAX(m.timestamp) as last_message_at
            FROM conversations c
            LEFT JOIN messages m ON c.conversation_id = m.conversation_id
            WHERE c.user_id = :user_id
            GROUP BY c.conversation_id, c.created_at, c.updated_at, c.metadata
            ORDER BY c.updated_at DESC
            LIMIT :limit OFFSET :offset
        """
        
        results = self.engine.execute_query(
            query,
            {
                "user_id": user_context.user_id,
                "limit": limit,
                "offset": offset,
            }
        )
        
        return [
            {
                "conversation_id": r["CONVERSATION_ID"],
                "created_at": r["CREATED_AT"].isoformat() if r["CREATED_AT"] else None,
                "updated_at": r["UPDATED_AT"].isoformat() if r["UPDATED_AT"] else None,
                "message_count": r["MESSAGE_COUNT"],
                "last_message_at": r["LAST_MESSAGE_AT"].isoformat() if r["LAST_MESSAGE_AT"] else None,
                "metadata": json.loads(r["METADATA"]) if r["METADATA"] else {},
            }
            for r in results
        ]
    
    async def add_message(
        self,
        conversation_id: str,
        user_context: UserContext,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: Conversation ID
            user_context: User context for validation
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional metadata
            
        Returns:
            Message dict
            
        Raises:
            ValidationException: If role is invalid
        """
        if role not in ["user", "assistant", "system"]:
            raise ValidationException(
                f"Invalid role: {role}. Must be user, assistant, or system"
            )
        
        # Verify conversation ownership
        await self.get_conversation(conversation_id, user_context)
        
        # Insert message
        query = """
            INSERT INTO messages (
                conversation_id,
                role,
                content,
                timestamp,
                metadata
            ) VALUES (
                :conversation_id,
                :role,
                :content,
                CURRENT_TIMESTAMP(),
                PARSE_JSON(:metadata)
            )
        """
        
        self.engine.execute_query(
            query,
            {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "metadata": json.dumps(metadata or {}),
            }
        )
        
        # Update conversation timestamp
        update_query = """
            UPDATE conversations
            SET updated_at = CURRENT_TIMESTAMP()
            WHERE conversation_id = :conversation_id
        """
        
        self.engine.execute_query(
            update_query,
            {"conversation_id": conversation_id}
        )
        
        logger.info(
            "Message added",
            conversation_id=conversation_id,
            role=role,
        )
        
        return {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
    
    async def get_messages(
        self,
        conversation_id: str,
        user_context: UserContext,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get messages for a conversation.
        
        Args:
            conversation_id: Conversation ID
            user_context: User context
            limit: Optional message limit
            
        Returns:
            List of message dicts
        """
        query = """
            SELECT 
                id,
                conversation_id,
                role,
                content,
                timestamp,
                metadata
            FROM messages
            WHERE conversation_id = :conversation_id
            ORDER BY timestamp ASC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        results = self.engine.execute_query(
            query,
            {"conversation_id": conversation_id}
        )
        
        return [
            {
                "id": r["ID"],
                "conversation_id": r["CONVERSATION_ID"],
                "role": r["ROLE"],
                "content": r["CONTENT"],
                "timestamp": r["TIMESTAMP"].isoformat() if r["TIMESTAMP"] else None,
                "metadata": json.loads(r["METADATA"]) if r["METADATA"] else {},
            }
            for r in results
        ]
    
    async def delete_conversation(
        self,
        conversation_id: str,
        user_context: UserContext,
    ) -> bool:
        """
        Delete a conversation and all its messages.
        
        Args:
            conversation_id: Conversation ID
            user_context: User context for validation
            
        Returns:
            True if deleted
        """
        # Verify ownership
        await self.get_conversation(conversation_id, user_context)
        
        # Delete messages
        delete_messages_query = """
            DELETE FROM messages
            WHERE conversation_id = :conversation_id
        """
        
        self.engine.execute_query(
            delete_messages_query,
            {"conversation_id": conversation_id}
        )
        
        # Delete conversation
        delete_conv_query = """
            DELETE FROM conversations
            WHERE conversation_id = :conversation_id
                AND user_id = :user_id
        """
        
        self.engine.execute_query(
            delete_conv_query,
            {
                "conversation_id": conversation_id,
                "user_id": user_context.user_id,
            }
        )
        
        logger.info(
            "Conversation deleted",
            conversation_id=conversation_id,
            user_id=user_context.user_id,
        )
        
        return True
    
    async def update_metadata(
        self,
        conversation_id: str,
        user_context: UserContext,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update conversation metadata.
        
        Args:
            conversation_id: Conversation ID
            user_context: User context
            metadata: New metadata
            
        Returns:
            Updated conversation dict
        """
        # Verify ownership
        await self.get_conversation(conversation_id, user_context)
        
        # Update metadata
        query = """
            UPDATE conversations
            SET metadata = PARSE_JSON(:metadata),
                updated_at = CURRENT_TIMESTAMP()
            WHERE conversation_id = :conversation_id
                AND user_id = :user_id
        """
        
        self.engine.execute_query(
            query,
            {
                "conversation_id": conversation_id,
                "user_id": user_context.user_id,
                "metadata": json.dumps(metadata),
            }
        )
        
        logger.info(
            "Conversation metadata updated",
            conversation_id=conversation_id,
        )
        
        return await self.get_conversation(conversation_id, user_context)


# Global instance
conversation_service = ConversationService()
