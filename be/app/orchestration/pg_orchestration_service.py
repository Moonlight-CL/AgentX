"""PostgreSQL implementation of OrchestrationService.

Overrides only _store_orchestration_session to write to PG session tables
instead of DynamoDB ChatSessionTable. All other methods are inherited.
"""

import json
from datetime import datetime, timezone
from typing import Any

from .service import OrchestrationService
from ..utils.pg_config import get_pg_connection
from strands.types.session import SessionType, SessionMessage
from strands.types.content import Message, ContentBlock


class PGOrchestrationService(OrchestrationService):
    """PostgreSQL-backed OrchestrationService.

    CRUD for orchestrations and chat records is delegated to the parent class
    which uses ChatRecordService internally. The only override needed is
    _store_orchestration_session which writes session data directly.
    """

    def __init__(self):
        # Call parent init; it sets up orchestration_table (DynamoDB) and chat_service
        # For PG backend we override the storage calls for sessions only
        from ..utils.aws_config import get_orchestration_table
        from ..agent.pg_agent_service import PGChatRecordService
        import asyncio

        self.orchestration_table = get_orchestration_table()
        self.chat_service = PGChatRecordService()
        self.running_tasks = {}
        self.cancellation_events = {}

    def _store_orchestration_session(
        self, result, orchestration_id: str, execution_id: str, user_id: str, input_message: str
    ):
        """Store multi-agent orchestration results in PG session tables."""
        try:
            current_time = datetime.now(timezone.utc).isoformat()

            # Create session record
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO chat_sessions (session_id, session_type, created_at, updated_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (session_id) DO NOTHING
                        """,
                        (execution_id, SessionType.AGENT.value, current_time, current_time),
                    )

            print(f"Created orchestration session {execution_id} for user {user_id}")

            # Collect node results
            node_results = []
            for node_id, node_result in result.results.items():
                agent_results = node_result.get_agent_results()
                for agent_result in agent_results:
                    message_content = str(agent_result)
                    if message_content.strip():
                        node_results.append({
                            "node_id": node_id,
                            "message": message_content.strip(),
                            "execution_time": getattr(node_result, "execution_time", 0),
                            "create_time": current_time,
                        })

            node_results.sort(key=lambda x: x["execution_time"])

            agent_session_id = f"{orchestration_id}_{execution_id}"

            # Store user message as message_id 0
            user_msg = Message(role="user", content=[ContentBlock(text=input_message)])
            session_user_msg = SessionMessage(
                message=user_msg, message_id=0,
                created_at=current_time, updated_at=current_time,
            )

            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO session_messages (session_id, agent_id, message_id,
                            message_content, created_at, updated_at)
                        VALUES (%s, %s, %s, %s::jsonb, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (
                            execution_id, agent_session_id, 0,
                            json.dumps(session_user_msg.to_dict()),
                            current_time, current_time,
                        ),
                    )

            # Store each assistant node result
            for i, node_result in enumerate(node_results):
                idx = i + 1
                node_id = node_result["node_id"]
                assistant_msg = Message(
                    role="assistant",
                    content=[ContentBlock(text=node_result["message"])],
                )
                session_assistant_msg = SessionMessage(
                    message=assistant_msg, message_id=idx,
                    created_at=node_result["create_time"],
                    updated_at=node_result["create_time"],
                )
                with get_pg_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO session_messages (session_id, agent_id, message_id,
                                message_content, created_at, updated_at)
                            VALUES (%s, %s, %s, %s::jsonb, %s, %s)
                            ON CONFLICT DO NOTHING
                            """,
                            (
                                execution_id,
                                f"{orchestration_id}_{node_id}",
                                idx,
                                json.dumps(session_assistant_msg.to_dict()),
                                node_result["create_time"],
                                node_result["create_time"],
                            ),
                        )

            print(f"Stored orchestration session with {len(node_results)} messages for execution {execution_id}")

        except Exception as e:
            print(f"Error storing orchestration session: {str(e)}")
            import traceback
            traceback.print_exc()
