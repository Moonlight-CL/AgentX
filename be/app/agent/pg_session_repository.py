"""PostgreSQL implementation of SessionRepository for agent session management."""

import json
import logging
import base64
from typing import Any, Optional, List
from datetime import datetime, timezone

from strands.session.session_repository import SessionRepository
from strands.types.session import Session, SessionAgent, SessionMessage
from ..utils.s3_storage import S3StorageService
from ..utils.pg_config import get_pg_connection

logger = logging.getLogger(__name__)


class PostgreSQLSessionRepository(SessionRepository):
    """PostgreSQL implementation of SessionRepository.

    Uses three tables: chat_sessions, session_agents, session_messages.
    S3 upload/download logic for attachments is identical to DynamoDBSessionRepository.
    """

    def __init__(self):
        self.s3_storage = S3StorageService()

    def create_session(self, session: Session, **kwargs: Any) -> Session:
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO chat_sessions (session_id, session_type, created_at, updated_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (session_id) DO NOTHING
                        """,
                        (
                            session.session_id,
                            session.session_type.value,
                            session.created_at,
                            session.updated_at,
                        ),
                    )
            logger.debug(f"Created session: {session.session_id}")
            return session
        except Exception as e:
            logger.error(f"Error creating session {session.session_id}: {e}")
            raise

    def read_session(self, session_id: str, **kwargs: Any) -> Optional[Session]:
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM chat_sessions WHERE session_id = %s",
                        (session_id,),
                    )
                    row = cur.fetchone()
                    if not row:
                        logger.debug(f"Session not found: {session_id}")
                        return None
                    col_names = [desc[0] for desc in cur.description]
                    item = dict(zip(col_names, row))
                    session = Session.from_dict({
                        'session_id': item['session_id'],
                        'session_type': item['session_type'],
                        'created_at': item['created_at'],
                        'updated_at': item['updated_at'],
                    })
            logger.debug(f"Read session: {session_id}")
            return session
        except Exception as e:
            logger.error(f"Error reading session {session_id}: {e}")
            raise

    def create_agent(self, session_id: str, session_agent: SessionAgent, **kwargs: Any) -> None:
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO session_agents (session_id, agent_id, state,
                            conversation_manager_state, created_at, updated_at)
                        VALUES (%s, %s, %s::jsonb, %s::jsonb, %s, %s)
                        ON CONFLICT (session_id, agent_id) DO NOTHING
                        """,
                        (
                            session_id,
                            session_agent.agent_id,
                            json.dumps(session_agent.state),
                            json.dumps(session_agent.conversation_manager_state),
                            session_agent.created_at,
                            session_agent.updated_at,
                        ),
                    )
            logger.debug(f"Created agent {session_agent.agent_id} in session {session_id}")
        except Exception as e:
            logger.error(f"Error creating agent {session_agent.agent_id} in session {session_id}: {e}")
            raise

    def read_agent(self, session_id: str, agent_id: str, **kwargs: Any) -> Optional[SessionAgent]:
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM session_agents WHERE session_id = %s AND agent_id = %s",
                        (session_id, agent_id),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    col_names = [desc[0] for desc in cur.description]
                    item = dict(zip(col_names, row))
                    state = item['state']
                    conv_state = item['conversation_manager_state']
                    if isinstance(state, str):
                        state = json.loads(state)
                    if isinstance(conv_state, str):
                        conv_state = json.loads(conv_state)
                    session_agent = SessionAgent.from_dict({
                        'agent_id': item['agent_id'],
                        'state': state,
                        'conversation_manager_state': conv_state,
                        'created_at': item['created_at'],
                        'updated_at': item['updated_at'],
                    })
            logger.debug(f"Read agent {agent_id} from session {session_id}")
            return session_agent
        except Exception as e:
            logger.error(f"Error reading agent {agent_id} from session {session_id}: {e}")
            raise

    def update_agent(self, session_id: str, session_agent: SessionAgent, **kwargs: Any) -> None:
        try:
            session_agent.updated_at = datetime.now(timezone.utc).isoformat()
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO session_agents (session_id, agent_id, state,
                            conversation_manager_state, created_at, updated_at)
                        VALUES (%s, %s, %s::jsonb, %s::jsonb, %s, %s)
                        ON CONFLICT (session_id, agent_id) DO UPDATE SET
                            state = EXCLUDED.state,
                            conversation_manager_state = EXCLUDED.conversation_manager_state,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (
                            session_id,
                            session_agent.agent_id,
                            json.dumps(session_agent.state),
                            json.dumps(session_agent.conversation_manager_state),
                            session_agent.created_at,
                            session_agent.updated_at,
                        ),
                    )
            logger.debug(f"Updated agent {session_agent.agent_id} in session {session_id}")
        except Exception as e:
            logger.error(f"Error updating agent {session_agent.agent_id} in session {session_id}: {e}")
            raise

    def create_message(self, session_id: str, agent_id: str, session_message: SessionMessage, **kwargs: Any) -> None:
        try:
            message_dict = session_message.to_dict()
            content_blocks = message_dict.get("message", {}).get("content", [])
            cinx = 0
            for c in content_blocks:
                file_data = None
                filename = f'{agent_id}#{session_message.message_id:06d}#{cinx:02d}'
                if c.get("image"):
                    file_data = base64.b64decode(c["image"]["source"]["bytes"]["data"])
                    c["image"]["source"]["bytes"]["data"] = ""
                    file_info = self.s3_storage.upload_file(file_content=file_data, filename=filename)
                    c["image"]["source"]["s3key"] = file_info["s3_key"]
                elif c.get("video"):
                    file_data = base64.b64decode(c["video"]["source"]["bytes"]["data"])
                    c["video"]["source"]["bytes"]["data"] = ""
                    file_info = self.s3_storage.upload_file(file_content=file_data, filename=filename)
                    c["video"]["source"]["s3key"] = file_info["s3_key"]
                elif c.get("document"):
                    file_data = base64.b64decode(c["document"]["source"]["bytes"]["data"])
                    c["document"]["source"]["bytes"]["data"] = ""
                    file_info = self.s3_storage.upload_file(file_content=file_data, filename=filename)
                    c["document"]["source"]["s3key"] = file_info["s3_key"]
                cinx += 1

            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO session_messages (session_id, agent_id, message_id,
                            message_content, created_at, updated_at)
                        VALUES (%s, %s, %s, %s::jsonb, %s, %s)
                        ON CONFLICT (session_id, agent_id, message_id) DO NOTHING
                        """,
                        (
                            session_id, agent_id, session_message.message_id,
                            json.dumps(message_dict),
                            session_message.created_at,
                            session_message.updated_at,
                        ),
                    )
            logger.debug(f"Created message {session_message.message_id} for agent {agent_id} in session {session_id}")
        except Exception as e:
            logger.error(f"Error creating message {session_message.message_id} for agent {agent_id}: {e}")
            raise

    def read_message(self, session_id: str, agent_id: str, message_id: int, **kwargs: Any) -> Optional[SessionMessage]:
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM session_messages WHERE session_id = %s AND agent_id = %s AND message_id = %s",
                        (session_id, agent_id, message_id),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    col_names = [desc[0] for desc in cur.description]
                    item = dict(zip(col_names, row))

            message_content = item['message_content']
            if isinstance(message_content, str):
                message_dict = json.loads(message_content)
            else:
                message_dict = message_content

            content_blocks = message_dict.get("message", {}).get("content", [])
            for c in content_blocks:
                if c.get("image"):
                    s3key = c["image"]["source"].get("s3key")
                    if s3key:
                        c["image"]["source"]["bytes"]["data"] = self.s3_storage.get_encoded_file(s3key)
                elif c.get("video"):
                    s3key = c["video"]["source"].get("s3key")
                    if s3key:
                        c["video"]["source"]["bytes"]["data"] = self.s3_storage.get_encoded_file(s3key)
                elif c.get("document"):
                    s3key = c["document"]["source"].get("s3key")
                    if s3key:
                        c["document"]["source"]["bytes"]["data"] = self.s3_storage.get_encoded_file(s3key)

            logger.debug(f"Read message {message_id} for agent {agent_id} from session {session_id}")
            return SessionMessage.from_dict(message_dict)
        except Exception as e:
            logger.error(f"Error reading message {message_id} for agent {agent_id}: {e}")
            raise

    def update_message(self, session_id: str, agent_id: str, session_message: SessionMessage, **kwargs: Any) -> None:
        try:
            session_message.updated_at = datetime.now(timezone.utc).isoformat()
            message_dict = session_message.to_dict()
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE session_messages SET message_content = %s::jsonb, updated_at = %s
                        WHERE session_id = %s AND agent_id = %s AND message_id = %s
                        """,
                        (
                            json.dumps(message_dict),
                            session_message.updated_at,
                            session_id, agent_id, session_message.message_id,
                        ),
                    )
            logger.debug(f"Updated message {session_message.message_id} for agent {agent_id} in session {session_id}")
        except Exception as e:
            logger.error(f"Error updating message {session_message.message_id} for agent {agent_id}: {e}")
            raise

    def list_messages(
        self, session_id: str, agent_id: str,
        limit: Optional[int] = None, offset: int = 0,
        **kwargs: Any
    ) -> List[SessionMessage]:
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    if limit is not None:
                        cur.execute(
                            """
                            SELECT * FROM session_messages
                            WHERE session_id = %s AND agent_id = %s
                            ORDER BY message_id ASC
                            LIMIT %s OFFSET %s
                            """,
                            (session_id, agent_id, limit, offset),
                        )
                    else:
                        cur.execute(
                            """
                            SELECT * FROM session_messages
                            WHERE session_id = %s AND agent_id = %s
                            ORDER BY message_id ASC
                            OFFSET %s
                            """,
                            (session_id, agent_id, offset),
                        )
                    rows = cur.fetchall()
                    col_names = [desc[0] for desc in cur.description]
                    items = [dict(zip(col_names, row)) for row in rows]

            read_attachment = kwargs.get("read_attachment", True) if kwargs else True
            messages = []
            for item in items:
                try:
                    message_content = item['message_content']
                    if isinstance(message_content, str):
                        message_dict = json.loads(message_content)
                    else:
                        message_dict = message_content

                    content_blocks = message_dict.get("message", {}).get("content", [])
                    for c in content_blocks:
                        if c.get("image"):
                            s3key = c["image"]["source"].get("s3key")
                            if s3key:
                                if read_attachment:
                                    c["image"]["source"]["bytes"]["data"] = self.s3_storage.get_encoded_file(s3key)
                                else:
                                    c["image"]["source"]["s3key"] = s3key
                        elif c.get("video"):
                            s3key = c["video"]["source"].get("s3key")
                            if s3key:
                                if read_attachment:
                                    c["video"]["source"]["bytes"]["data"] = self.s3_storage.get_encoded_file(s3key)
                                else:
                                    c["video"]["source"]["s3key"] = s3key
                        elif c.get("document"):
                            s3key = c["document"]["source"].get("s3key")
                            if s3key:
                                if read_attachment:
                                    c["document"]["source"]["bytes"]["data"] = self.s3_storage.get_encoded_file(s3key)
                                else:
                                    c["document"]["source"]["s3key"] = s3key

                    messages.append(SessionMessage.from_dict(message_dict))
                except Exception as e:
                    logger.warning(f"Error parsing message {item.get('message_id', 'unknown')}: {e}")
                    continue

            logger.debug(f"Listed {len(messages)} messages for agent {agent_id} in session {session_id}")
            return messages
        except Exception as e:
            logger.error(f"Error listing messages for agent {agent_id} in session {session_id}: {e}")
            raise
