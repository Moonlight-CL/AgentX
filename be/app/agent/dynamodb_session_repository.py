"""DynamoDB implementation of SessionRepository for agent session management."""

import json
import logging
import base64
from typing import Any, Optional, List
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key, Attr

from strands.session.session_repository import SessionRepository
from strands.types.session import Session, SessionAgent, SessionMessage
from ..utils.s3_storage import S3StorageService
from ..utils.aws_config import get_aws_region, get_dynamodb_resource

logger = logging.getLogger(__name__)


class DynamoDBSessionRepository(SessionRepository):
    """DynamoDB implementation of SessionRepository.
    
    This implementation uses a single DynamoDB table to store sessions, agents, and messages
    with a hierarchical structure using composite keys.
    
    Table Structure:
    - PK (Partition Key): session_id
    - SK (Sort Key): 
      - "SESSION" for session metadata
      - "AGENT#{agent_id}" for agent data
      - "MESSAGE#{agent_id}#{message_id:06d}" for messages (zero-padded for proper sorting)
    
    This design allows efficient querying of:
    - Session metadata
    - All agents in a session
    - All messages for a specific agent
    - Paginated message retrieval
    """
    
    def __init__(self, table_name: str = "ChatSessionTable"):
        """Initialize the DynamoDB session repository.
        
        Args:
            table_name: Name of the DynamoDB table to use for session storage
        """
        self.table_name = table_name
        self.dynamodb = get_dynamodb_resource()
        self.table = self.dynamodb.Table(table_name)
        self.s3_storage = S3StorageService()
    
    def create_session(self, session: Session, **kwargs: Any) -> Session:
        """Create a new Session in DynamoDB.
        
        Args:
            session: Session object to create
            **kwargs: Additional keyword arguments
            
        Returns:
            The created Session object
        """
        try:
            item = {
                'PK': session.session_id,
                'SK': 'SESSION',
                'session_id': session.session_id,
                'session_type': session.session_type.value,
                'created_at': session.created_at,
                'updated_at': session.updated_at,
                'record_type': 'session'
            }
            
            self.table.put_item(Item=item)
            logger.debug(f"Created session: {session.session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Error creating session {session.session_id}: {e}")
            raise
    
    def read_session(self, session_id: str, **kwargs: Any) -> Optional[Session]:
        """Read a Session from DynamoDB.
        
        Args:
            session_id: ID of the session to read
            **kwargs: Additional keyword arguments
            
        Returns:
            Session object if found, None otherwise
        """
        try:
            response = self.table.get_item(
                Key={
                    'PK': session_id,
                    'SK': 'SESSION'
                }
            )
            
            if 'Item' not in response:
                logger.debug(f"Session not found: {session_id}")
                return None
            
            item = response['Item']
            session = Session.from_dict({
                'session_id': item['session_id'],
                'session_type': item['session_type'],
                'created_at': item['created_at'],
                'updated_at': item['updated_at']
            })
            
            logger.debug(f"Read session: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Error reading session {session_id}: {e}")
            raise
    
    def create_agent(self, session_id: str, session_agent: SessionAgent, **kwargs: Any) -> None:
        """Create a new Agent in a Session.
        
        Args:
            session_id: ID of the session
            session_agent: SessionAgent object to create
            **kwargs: Additional keyword arguments
        """
        try:
            item = {
                'PK': session_id,
                'SK': f'AGENT#{session_agent.agent_id}',
                'session_id': session_id,
                'agent_id': session_agent.agent_id,
                'state': json.dumps(session_agent.state),
                'conversation_manager_state': json.dumps(session_agent.conversation_manager_state),
                'created_at': session_agent.created_at,
                'updated_at': session_agent.updated_at,
                'record_type': 'agent'
            }
            
            self.table.put_item(Item=item)
            logger.debug(f"Created agent {session_agent.agent_id} in session {session_id}")
            
        except Exception as e:
            logger.error(f"Error creating agent {session_agent.agent_id} in session {session_id}: {e}")
            raise
    
    def read_agent(self, session_id: str, agent_id: str, **kwargs: Any) -> Optional[SessionAgent]:
        """Read an Agent from a Session.
        
        Args:
            session_id: ID of the session
            agent_id: ID of the agent to read
            **kwargs: Additional keyword arguments
            
        Returns:
            SessionAgent object if found, None otherwise
        """
        try:
            response = self.table.get_item(
                Key={
                    'PK': session_id,
                    'SK': f'AGENT#{agent_id}'
                }
            )
            
            if 'Item' not in response:
                logger.debug(f"Agent not found: {agent_id} in session {session_id}")
                return None
            
            item = response['Item']
            session_agent = SessionAgent.from_dict({
                'agent_id': item['agent_id'],
                'state': json.loads(item['state']),
                'conversation_manager_state': json.loads(item['conversation_manager_state']),
                'created_at': item['created_at'],
                'updated_at': item['updated_at']
            })
            
            logger.debug(f"Read agent {agent_id} from session {session_id}")
            return session_agent
            
        except Exception as e:
            logger.error(f"Error reading agent {agent_id} from session {session_id}: {e}")
            raise
    
    def update_agent(self, session_id: str, session_agent: SessionAgent, **kwargs: Any) -> None:
        """Update an Agent in a Session.
        
        Args:
            session_id: ID of the session
            session_agent: SessionAgent object with updated data
            **kwargs: Additional keyword arguments
        """
        try:
            # Update the updated_at timestamp
            session_agent.updated_at = datetime.now(timezone.utc).isoformat()
            
            item = {
                'PK': session_id,
                'SK': f'AGENT#{session_agent.agent_id}',
                'session_id': session_id,
                'agent_id': session_agent.agent_id,
                'state': json.dumps(session_agent.state),
                'conversation_manager_state': json.dumps(session_agent.conversation_manager_state),
                'created_at': session_agent.created_at,
                'updated_at': session_agent.updated_at,
                'record_type': 'agent'
            }
            
            self.table.put_item(Item=item)
            logger.debug(f"Updated agent {session_agent.agent_id} in session {session_id}")
            
        except Exception as e:
            logger.error(f"Error updating agent {session_agent.agent_id} in session {session_id}: {e}")
            raise
    
    def create_message(self, session_id: str, agent_id: str, session_message: SessionMessage, **kwargs: Any) -> None:
        """Create a new Message for an Agent.
        
        Args:
            session_id: ID of the session
            agent_id: ID of the agent
            session_message: SessionMessage object to create
            **kwargs: Additional keyword arguments
        """
        try:
            # Convert message to dict for JSON serialization
            message_dict = session_message.to_dict()

            content_blocks = message_dict.get("message").get("content")
            cinx = 0
            for c in content_blocks:
                file_data = None
                filename = f'{agent_id}#{session_message.message_id:06d}#{cinx: 02d}'
                if c.get("image"):
                    file_data = base64.b64decode(c.get("image").get("source").get("bytes").get("data"))
                    c["image"]["source"]["bytes"]["data"] = ""

                    file_info = self.s3_storage.upload_file(file_content= file_data, filename= filename)
                    c["image"]["source"]["s3key"] = file_info["s3_key"]
                elif c.get("video"):
                    file_data = base64.b64decode(c.get("video").get("source").get("bytes").get("data"))
                    c["video"]["source"]["bytes"]["data"] = ""

                    file_info = self.s3_storage.upload_file(file_content= file_data, filename= filename)
                    c["video"]["source"]["s3key"] = file_info["s3_key"]
                elif c.get("document"):
                    file_data = base64.b64decode(c.get("document").get("source").get("bytes").get("data"))
                    c["document"]["source"]["bytes"]["data"] = ""

                    file_info = self.s3_storage.upload_file(file_content= file_data, filename= filename)
                    c["document"]["source"]["s3key"] = file_info["s3_key"]
                
                cinx +=1

            item = {
                'PK': session_id,
                'SK': f'MESSAGE#{agent_id}#{session_message.message_id:06d}',
                'session_id': session_id,
                'agent_id': agent_id,
                'message_id': session_message.message_id,
                'message_content': json.dumps(message_dict),
                'created_at': session_message.created_at,
                'updated_at': session_message.updated_at,
                'record_type': 'message'
            }
            
            self.table.put_item(Item=item)
            logger.debug(f"Created message {session_message.message_id} for agent {agent_id} in session {session_id}")
            
        except Exception as e:
            logger.error(f"Error creating message {session_message.message_id} for agent {agent_id} in session {session_id}: {e}")
            raise
    
    def read_message(self, session_id: str, agent_id: str, message_id: int, **kwargs: Any) -> Optional[SessionMessage]:
        """Read a Message from an Agent.
        
        Args:
            session_id: ID of the session
            agent_id: ID of the agent
            message_id: ID of the message to read
            **kwargs: Additional keyword arguments
            
        Returns:
            SessionMessage object if found, None otherwise
        """
        try:
            response = self.table.get_item(
                Key={
                    'PK': session_id,
                    'SK': f'MESSAGE#{agent_id}#{message_id:06d}'
                }
            )
            
            if 'Item' not in response:
                logger.debug(f"Message not found: {message_id} for agent {agent_id} in session {session_id}")
                return None
            
            item = response['Item']
            message_dict = json.loads(item['message_content'])
            content_blocks = message_dict.get("message").get("content")

            for c in content_blocks:
                if c.get("image"):
                    s3key = c.get("image").get("source").get("s3key")
                    data = self.s3_storage.get_encoded_file(s3key)
                    print(f"s3key: {s3key}")
                    c["image"]["source"]["bytes"]["data"] = data
                elif c.get("video"):
                    s3key = c.get("video").get("source").get("s3key")
                    data = self.s3_storage.get_encoded_file(s3key)
                    c["video"]["source"]["bytes"]["data"] = data
                elif c.get("document"):
                    s3key = c.get("document").get("source").get("s3key")
                    data = self.s3_storage.get_encoded_file(s3key)
                    c["document"]["source"]["bytes"]["data"] = data

            session_message = SessionMessage.from_dict(message_dict)
            
            logger.debug(f"Read message {message_id} for agent {agent_id} from session {session_id}")
            return session_message
            
        except Exception as e:
            logger.error(f"Error reading message {message_id} for agent {agent_id} from session {session_id}: {e}")
            raise
    
    def update_message(self, session_id: str, agent_id: str, session_message: SessionMessage, **kwargs: Any) -> None:
        """Update a Message (usually for redaction).
        
        Args:
            session_id: ID of the session
            agent_id: ID of the agent
            session_message: SessionMessage object with updated data
            **kwargs: Additional keyword arguments
        """
        try:
            # Update the updated_at timestamp
            session_message.updated_at = datetime.now(timezone.utc).isoformat()
            
            # Convert message to dict for JSON serialization
            message_dict = session_message.to_dict()
            
            item = {
                'PK': session_id,
                'SK': f'MESSAGE#{agent_id}#{session_message.message_id:06d}',
                'session_id': session_id,
                'agent_id': agent_id,
                'message_id': session_message.message_id,
                'message_content': json.dumps(message_dict),
                'created_at': session_message.created_at,
                'updated_at': session_message.updated_at,
                'record_type': 'message'
            }
            
            self.table.put_item(Item=item)
            logger.debug(f"Updated message {session_message.message_id} for agent {agent_id} in session {session_id}")
            
        except Exception as e:
            logger.error(f"Error updating message {session_message.message_id} for agent {agent_id} in session {session_id}: {e}")
            raise
    
    def list_messages(
        self, 
        session_id: str, 
        agent_id: str, 
        limit: Optional[int] = None, 
        offset: int = 0, 
        **kwargs: Any
    ) -> List[SessionMessage]:
        """List Messages from an Agent with pagination.
        
        Args:
            session_id: ID of the session
            agent_id: ID of the agent
            limit: Maximum number of messages to return
            offset: Number of messages to skip (for pagination)
            **kwargs: Additional keyword arguments
            
        Returns:
            List of SessionMessage objects
        """
        try:
            # Build the query parameters
            query_params = {
                'KeyConditionExpression': Key('PK').eq(session_id) & Key('SK').begins_with(f'MESSAGE#{agent_id}#'),
                'ScanIndexForward': True  # Sort in ascending order by message_id
            }
            
            # Add limit if specified
            if limit is not None:
                query_params['Limit'] = limit + offset  # We'll slice later to handle offset
            
            response = self.table.query(**query_params)
            items = response.get('Items', [])
            
            # Handle pagination with offset
            if offset > 0:
                items = items[offset:]
            
            if limit is not None and len(items) > limit:
                items = items[:limit]
            
            if kwargs:
                read_attachment = kwargs.get("read_attachment", True)
            else:
                read_attachment = True
            
            # Convert items to SessionMessage objects
            messages = []
            for item in items:
                try:
                    message_dict = json.loads(item['message_content'])
                    
                    content_blocks = message_dict.get("message").get("content")
                    for c in content_blocks:
                        if c.get("image"):
                            s3key = c.get("image").get("source").get("s3key")
                            if read_attachment:
                                data = self.s3_storage.get_encoded_file(s3key)
                                c["image"]["source"]["bytes"]["data"] = data
                            else:
                                c["image"]["source"]["s3key"] = s3key
                            
                        elif c.get("video"):
                            s3key = c.get("video").get("source").get("s3key")
                            if read_attachment:
                                data = self.s3_storage.get_encoded_file(s3key)
                                c["video"]["source"]["bytes"]["data"] = data
                            else:
                                c["video"]["source"]["s3key"] = s3key

                        elif c.get("document"):
                            s3key = c.get("document").get("source").get("s3key")
                            if read_attachment:
                                data = self.s3_storage.get_encoded_file(s3key)
                                c["document"]["source"]["bytes"]["data"] = data
                            else:
                                c["document"]["source"]["s3key"] = s3key

                    session_message = SessionMessage.from_dict(message_dict)
                    messages.append(session_message)
                except Exception as e:
                    logger.warning(f"Error parsing message {item.get('message_id', 'unknown')}: {e}")
                    continue
            
            logger.debug(f"Listed {len(messages)} messages for agent {agent_id} in session {session_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Error listing messages for agent {agent_id} in session {session_id}: {e}")
            raise
