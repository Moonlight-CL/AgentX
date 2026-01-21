"""
AgentCore Runtime invocation handler.
This module handles the /invocations endpoint logic required by AgentCore Runtime.
"""
from datetime import datetime
from typing import Dict, Optional, AsyncGenerator
import uuid

from ..agent.agent import AgentPOService, ChatRecord, ChatRecordService
from ..agent.event_serializer import EventSerializer


class AgentCoreInvocationHandler:
    """Handler for AgentCore Runtime invocation requests."""

    def __init__(self):
        self.agent_service = AgentPOService()
        self.chat_record_service = ChatRecordService()

    async def parse_invocation_request(self, data: dict) -> Dict:
        """
        Parse AgentCore invocation request payload.

        Expected input format:
        {
            "input": {
                "agent_id": "agent_id",
                "prompt": "user message",
                "session_id": "optional_session_id",
                "user_id": "optional_user_id",
                "file_attachments": [],  # optional
                "chat_record_enabled": true,  # optional, default True
                "use_s3_reference": false,  # optional, default False
                "agent_owner_id": "optional_owner_id"  # optional
            }
        }

        :param data: Request JSON data
        :return: Parsed parameters dictionary
        :raises ValueError: If required parameters are missing
        """
        input_data = data.get("input", {})

        # Extract parameters
        agent_id = input_data.get("agent_id")
        user_message = input_data.get("prompt", "")
        session_id = input_data.get("session_id")
        user_id = input_data.get("user_id", "public")
        file_attachments = input_data.get("file_attachments", [])
        use_s3_reference = input_data.get("use_s3_reference", False)
        agent_owner_id = input_data.get("agent_owner_id")
        chat_record_enabled = input_data.get("chat_record_enabled", True)  # Default to True

        # Validate required parameters
        if not agent_id:
            raise ValueError("agent_id is required in input")

        if not user_message:
            raise ValueError("prompt is required in input")

        # Generate session_id if not provided
        if not session_id:
            session_id = f"{uuid.uuid4().hex}{datetime.now().strftime('%Y%m%d%H%M%S')}"

        return {
            "agent_id": agent_id,
            "user_message": user_message,
            "session_id": session_id,
            "user_id": user_id,
            "file_attachments": file_attachments,
            "use_s3_reference": use_s3_reference,
            "agent_owner_id": agent_owner_id,
            "chat_record_enabled": chat_record_enabled
        }

    def create_chat_record_if_enabled(
        self,
        chat_record_enabled: bool,
        session_id: str,
        agent_id: str,
        user_id: str,
        user_message: str
    ) -> None:
        """
        Create chat record if enabled.

        :param chat_record_enabled: Whether to create chat record
        :param session_id: Session ID
        :param agent_id: Agent ID
        :param user_id: User ID
        :param user_message: User message
        """
        if chat_record_enabled:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            chat_record = ChatRecord(
                id=session_id,
                agent_id=agent_id,
                user_id=user_id,
                user_message=user_message,
                create_time=current_time
            )
            self.chat_record_service.add_chat_record(chat_record)

    async def process_invocation(
        self,
        agent_id: str,
        user_message: str,
        session_id: str,
        user_id: str,
        file_attachments: Optional[list] = None,
        use_s3_reference: bool = False,
        agent_owner_id: Optional[str] = None
    ) -> AsyncGenerator[Dict, None]:
        """
        Process agent invocation and stream events.
        Reuses the same logic as stream_chat in agent.py router.

        :param agent_id: Agent ID
        :param user_message: User message
        :param session_id: Session ID
        :param user_id: User ID
        :param file_attachments: Optional file attachments
        :param use_s3_reference: Whether to use S3 references
        :param agent_owner_id: Optional agent owner ID
        :yield: Event dictionaries
        """
        from .agent import process_chat_events_with_session

        # First, send the session_id to the client
        session_event = {
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        yield session_event

        # Stream events using the same logic as stream_chat
        async for event in process_chat_events_with_session(
            user_id=user_id,
            agent_id=agent_id,
            user_input=user_message,
            chat_id=session_id,
            file_attachments=file_attachments,
            chat_record_enabled=True,  # Always enabled for AgentCore invocations
            use_s3_reference=use_s3_reference,
            agent_owner_id=agent_owner_id,
            running_in_agentcore=True
        ):
            yield event

    async def handle_invocation_stream(self, data: dict) -> AsyncGenerator[str, None]:
        """
        Handle complete invocation flow and generate SSE stream.

        :param data: Request JSON data
        :yield: SSE formatted events
        """
        try:
            # Parse request
            params = await self.parse_invocation_request(data)

            # Create chat record if enabled
            self.create_chat_record_if_enabled(
                chat_record_enabled=params["chat_record_enabled"],
                session_id=params["session_id"],
                agent_id=params["agent_id"],
                user_id=params["user_id"],
                user_message=params["user_message"]
            )

            # Process invocation and stream events
            async for event in self.process_invocation(
                agent_id=params["agent_id"],
                user_message=params["user_message"],
                session_id=params["session_id"],
                user_id=params["user_id"],
                file_attachments=params["file_attachments"],
                use_s3_reference=params["use_s3_reference"],
                agent_owner_id=params["agent_owner_id"]
            ):
                yield EventSerializer.format_as_sse(event)

        except ValueError as e:
            # Send validation error event
            error_event = {
                "type": "error",
                "error": {
                    "message": str(e)
                }
            }
            yield EventSerializer.format_as_sse(error_event)
        except Exception as e:
            print(f"Error in invocation handler: {str(e)}")
            import traceback
            traceback.print_exc()
            # Send error event
            error_event = {
                "type": "error",
                "error": {
                    "message": f"Agent processing failed: {str(e)}"
                }
            }
            yield EventSerializer.format_as_sse(error_event)
