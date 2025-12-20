from datetime import datetime
import uuid
import json
from dataclasses import dataclass

from fastapi import APIRouter, Request, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Dict, Optional, AsyncGenerator
from ..agent.agent import AgentPO, AgentType, ModelProvider, AgentTool, AgentPOService, ChatRecord, ChatResponse, ChatRecordService
from ..agent.event_serializer import EventSerializer
from ..utils.content_converter import ContentConverter
from ..user.auth import get_current_user

@dataclass
class ChatRequestData:
    """
    Data class to hold parsed chat request information
    """
    agent_id: Optional[str]
    user_message: Optional[str]
    chat_id: str
    chat_record_enabled: bool
    user_id: str
    file_attachments: Optional[List[Dict]]
    use_s3_reference: bool
    agent_owner_id: Optional[str]  # Owner ID for shared agents

agent_service = AgentPOService()
chat_reccord_service = ChatRecordService()

router = APIRouter(
    prefix="/agent",
    tags=["agent"],
    responses={404: {"description": "Not found"}}
)

@router.get("/list")
def list_agents(current_user: dict = Depends(get_current_user)) -> List[AgentPO]:
    """
    List all agents for the current user.
    :return: A list of agents.
    """
    user_id = current_user.get('user_id', 'public')
    user_groups = current_user.get('user_groups', [])
    return agent_service.list_agents(user_id, user_groups)

@router.get("/get/{agent_id}")
def get_agent(agent_id: str, current_user: dict = Depends(get_current_user)) -> AgentPO:
    """
    Get a specific agent by ID.
    :param agent_id: The ID of the agent to retrieve.
    :return: Details of the specified agent.
    """
    user_id = current_user.get('user_id', 'public')
    agent = agent_service.get_agent(user_id, agent_id)
    if not agent:
        raise ValueError(f"Agent with ID {agent_id} not found.")
    return agent

@router.delete("/delete/{agent_id}")
def delete_agent(agent_id: str, current_user: dict = Depends(get_current_user)) -> bool:
    """
    Delete a specific agent by ID.
    :param agent_id: The ID of the agent to delete.
    :return: True if deletion was successful, False otherwise.
    """
    user_id = current_user.get('user_id', 'public')
    return agent_service.delete_agent(user_id, agent_id)

@router.post("/createOrUpdate")
async def create_agent(request: Request, current_user: dict = Depends(get_current_user)) -> AgentPO:
    """
    Create a new agent.
    :param agent: The agent data to create.
    :return: Confirmation of agent creation.
    """
    user_id = current_user.get('user_id', 'public')
    agent = await request.json()
    agent_id = uuid.uuid4().hex
    if agent and agent.get("id"):
        agent_service.delete_agent(user_id, agent["id"])
        agent_id = agent["id"]

    tools = []
    if agent.get("tools"):
        tools = [t for tool in agent["tools"] if (t:= AgentTool.model_validate(tool)) is not None]

    agent_po = AgentPO(
        id= agent_id,
        name=agent.get("name"),
        display_name=agent.get("display_name"),
        description=agent.get("description"),
        agent_type=AgentType(agent.get("agent_type")),
        model_provider=ModelProvider(agent.get("model_provider")),
        model_id=agent.get("model_id"),
        sys_prompt=agent.get("sys_prompt"),
        tools= tools,
        envs=agent.get("envs", ""),
        extras=agent.get("extras"),
    )
    agent_service.add_agent(agent_po, user_id)
    return agent_po

async def parse_chat_request_and_add_record(request: Request) -> ChatRequestData:
    """
    Parse a chat request to extract agent_id, user_message, file_attachments, and handle chat record.
    
    :param request: The request containing the chat parameters.
    :return: ChatRequestData object containing all parsed information.
    """
    data = await request.json()
    agent_id = data.get("agent_id")
    user_message = data.get("user_message")
    file_attachments = data.get("file_attachments", [])  # List of file info from S3 uploads
    chat_record_id = data.get("chat_record_id")  # New parameter for continuing conversation
    chat_record_enabled = data.get("chat_record_enabled", True)  # Default to True if not provided
    use_s3_reference = data.get("use_s3_reference", False)  # Default to False (existing behavior)
    agent_owner_id = data.get("agent_owner_id")  # Owner ID for shared agents
    
    # Get current user from request state (set by AuthMiddleware)
    current_user = getattr(request.state, 'current_user', None)
    user_id = current_user.get('user_id', '') if current_user else ''
    if user_id and user_id == 'service_account':
        user_id = data.get("user_id")
        agent_owner_id = data.get("agent_owner_id")
    
    # Handle chat record creation or continuation
    if chat_record_id:
        # Check if the chat record exists
        existing_record = chat_reccord_service.get_chat_record(user_id, chat_record_id)
        if existing_record:
            # Use existing chat record ID as session ID
            chat_id = chat_record_id
        else:
            # Chat record doesn't exist, create a new one
            chat_id = uuid.uuid4().hex
            if chat_record_enabled:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                chat_record = ChatRecord(
                    id=chat_id, 
                    agent_id=agent_id, 
                    user_id=user_id,
                    user_message=user_message, 
                    create_time=current_time
                )
                chat_reccord_service.add_chat_record(chat_record)
    else:
        # Create a new chat record
        chat_id = uuid.uuid4().hex
        if chat_record_enabled:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            chat_record = ChatRecord(
                id=chat_id, 
                agent_id=agent_id, 
                user_id=user_id,
                user_message=user_message, 
                create_time=current_time
            )
            chat_reccord_service.add_chat_record(chat_record)
    
    return ChatRequestData(
        agent_id=agent_id,
        user_message=user_message,
        chat_id=chat_id,
        chat_record_enabled=chat_record_enabled,
        user_id=user_id,
        file_attachments=file_attachments,
        use_s3_reference=use_s3_reference,
        agent_owner_id=agent_owner_id
    )

async def process_chat_events_with_session(user_id: str, agent_id: str, user_input: str, chat_id: str, file_attachments: Optional[List[Dict]] = None, chat_record_enabled: bool = True, use_s3_reference: bool = False, agent_owner_id: Optional[str] = None) -> AsyncGenerator[Dict, None]:
    """
    Process chat events using session management. Chat content is automatically stored in ChatSessionTable via DynamoDBSessionRepository.
    
    :param user_id: The user ID for data isolation.
    :param agent_id: The ID of the agent to chat with.
    :param user_input: The user's message or content blocks to process.
    :param chat_id: The ID of the chat record (used as session_id).
    :param file_attachments: List of file attachment info from S3.
    :param chat_record_enabled: Whether chat recording is enabled (for compatibility).
    :param use_s3_reference: Whether to use S3 references instead of binary content.
    :param agent_owner_id: The owner ID for shared agents.
    :yield: Chat events.
    """
    # Use agent_owner_id if provided (for shared agents), otherwise use current user_id
    lookup_user_id = agent_owner_id if agent_owner_id else user_id
    agent = agent_service.get_agent(lookup_user_id, agent_id)
    if not agent:
        raise ValueError(f"Agent with ID {agent_id} not found.")
    
    # Build agent with session management using chat_id as session_id
    agent_instance = agent_service.build_strands_agent_with_session(agent, chat_id, user_id=user_id)
    
    # Convert text and files to content blocks if files are present
    if file_attachments:
        content_converter = ContentConverter()
        content_blocks = content_converter.create_content_blocks(user_input, file_attachments, use_s3_reference)
        # Stream events with content blocks
        async for event in agent_instance.stream_async(content_blocks):
            yield event
    else:
        # Stream events with plain text - session management automatically handles message storage
        async for event in agent_instance.stream_async(user_input):
            yield event

async def process_chat_events(user_id: str, agent_id: str, user_message: str, chat_id: str, chat_record_enabled: bool = True) -> AsyncGenerator[Dict, None]:
    """
    Process chat events and save responses to the database if chat_record_enabled is True.
    
    :param user_id: The user ID for data isolation.
    :param agent_id: The ID of the agent to chat with.
    :param user_message: The user's message to process.
    :param chat_id: The ID of the chat record.
    :param chat_record_enabled: Whether to save chat responses to the database.
    :yield: Chat events.
    """
    # resp_no = 0
    async for event in agent_service.stream_chat(user_id= user_id, agent_id=agent_id, chat_id=chat_id, user_message=user_message, session_id=chat_id):
        # if chat_record_enabled and ("message" in event and "role" in event["message"]):
        #     chat_resp = ChatResponse(
        #         chat_id=chat_id, 
        #         resp_no=resp_no, 
        #         content=json.dumps(event), 
        #         create_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        #     )
        #     chat_reccord_service.add_chat_response(chat_resp)
        #     resp_no += 1
        yield event

@router.post("/stream_chat")
async def stream_chat(request: Request) -> StreamingResponse:
    """
    Stream chat messages from an agent using session management.
    :param request: The request containing the chat parameters.
    :return: A stream of chat messages.
    """
    chat_data = await parse_chat_request_and_add_record(request)
    
    if not chat_data.agent_id or not chat_data.user_message:
        return "Agent ID and user message are required."
    
    async def event_generator():
        """
        Generator function to yield SSE formatted events.
        """
        # First, send the chat_id to the frontend for session tracking
        chat_id_event = {"chat_id": chat_data.chat_id}
        yield EventSerializer.format_as_sse(chat_id_event)
        
        # Then stream the actual chat events
        async for event in process_chat_events_with_session(
            chat_data.user_id, 
            chat_data.agent_id, 
            chat_data.user_message, 
            chat_data.chat_id, 
            chat_data.file_attachments, 
            chat_data.chat_record_enabled, 
            chat_data.use_s3_reference,
            chat_data.agent_owner_id
        ):
            # Format the event as an SSE
            yield EventSerializer.format_as_sse(event)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.post("/stream_chat_legacy")
async def stream_chat_legacy(request: Request) -> StreamingResponse:
    """
    Stream chat messages from an agent using legacy approach (without session management).
    :param request: The request containing the chat parameters.
    :return: A stream of chat messages.
    """
    chat_data = await parse_chat_request_and_add_record(request)
    
    if not chat_data.agent_id or not chat_data.user_message:
        return "Agent ID and user message are required."
    
    async def event_generator():
        """
        Generator function to yield SSE formatted events.
        """
        async for event in process_chat_events(
            chat_data.user_id, 
            chat_data.agent_id, 
            chat_data.user_message, 
            chat_data.chat_id, 
            chat_data.chat_record_enabled
        ):
            # Format the event as an SSE
            yield EventSerializer.format_as_sse(event)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.post("/async_chat")
async def async_chat(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    """
    Process chat messages from an agent asynchronously.
    This endpoint returns immediately with a chat ID and processes the request in the background.
    
    :param request: The request containing the chat parameters.
    :param background_tasks: FastAPI's BackgroundTasks for background processing.
    :return: A JSON response with the chat ID.
    """
    chat_data = await parse_chat_request_and_add_record(request)
    
    if not chat_data.agent_id or not chat_data.user_message:
        return JSONResponse(
            status_code=400,
            content={"error": "Agent ID and user message are required."}
        )
    
    # Add the processing task to background tasks
    background_tasks.add_task(
        process_chat_in_background,
        user_id=chat_data.user_id,
        agent_id=chat_data.agent_id,
        user_message=chat_data.user_message,
        chat_id=chat_data.chat_id,
        chat_record_enabled=chat_data.chat_record_enabled
    )
    
    # Return immediately with the chat ID
    return JSONResponse(
        content={
            "status": "processing",
            "chat_id": chat_data.chat_id,
            "message": "Your request is being processed in the background."
        }
    )

async def process_chat_in_background(user_id: str, agent_id: str, user_message: str, chat_id: str, chat_record_enabled: bool = True):
    """
    Process a chat message in the background.
    
    :param user_id: The user ID for data isolation.
    :param agent_id: The ID of the agent to chat with.
    :param user_message: The user's message to process.
    :param chat_id: The ID of the chat record.
    :param chat_record_enabled: Whether to save chat responses to the database.
    """
    try:
        async for _ in process_chat_events(user_id, agent_id, user_message, chat_id, chat_record_enabled):
            pass  # We just need to consume the generator
        print(f"Background processing completed for chat {chat_id}")
    except Exception as e:
        # Log the error
        print(f"Error in background processing for chat {chat_id}: {str(e)}")

@router.get("/tool_list")
def available_agent_tools(current_user: dict = Depends(get_current_user)) -> List[AgentTool]:
    """
    List all available agent tools for the current user.
    :return: A list of available agent tools.
    """
    user_id = current_user.get('user_id', 'public')
    return agent_service.get_all_available_tools(user_id)

# Agent sharing endpoints
@router.post("/{agent_id}/share")
async def share_agent(
    agent_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
) -> JSONResponse:
    """
    Share an agent with specific users or groups.
    
    :param agent_id: The ID of the agent to share.
    :param request: Request containing sharing data.
    :param current_user: Current user from JWT token.
    :return: Success message.
    """
    user_id = current_user.get('user_id')
    
    # Parse sharing data
    data = await request.json()
    is_public = data.get("is_public", False)
    
    # Apply business logic based on is_public setting
    if is_public:
        # When public, clear shared_users and shared_groups
        shared_users = []
        shared_groups = []
    else:
        # When not public, use the provided values
        shared_users = data.get("shared_users", [])
        shared_groups = data.get("shared_groups", [])
    
    # Update agent sharing settings using service method
    success, error_msg = agent_service.update_agent_sharing(
        user_id=user_id,
        agent_id=agent_id,
        shared_users=shared_users,
        shared_groups=shared_groups,
        is_public=is_public
    )
    
    if success:
        return JSONResponse(
            content={
                "success": True,
                "message": "Agent sharing settings updated successfully"
            }
        )
    else:
        status_code = 404 if "not found" in error_msg.lower() or "permission" in error_msg.lower() else 500
        return JSONResponse(
            status_code=status_code,
            content={"error": error_msg}
        )

@router.get("/{agent_id}/sharing")
def get_agent_sharing(
    agent_id: str,
    current_user: dict = Depends(get_current_user)
) -> JSONResponse:
    """
    Get sharing settings for an agent.
    
    :param agent_id: The ID of the agent.
    :param current_user: Current user from JWT token.
    :return: Agent sharing settings.
    """
    user_id = current_user.get('user_id')
    
    # Get sharing info using service method
    sharing_info, error_msg = agent_service.get_agent_sharing_info(user_id, agent_id)
    
    if sharing_info:
        return JSONResponse(
            content={
                "success": True,
                "data": sharing_info
            }
        )
    else:
        return JSONResponse(
            status_code=404,
            content={"error": error_msg}
        )

@router.post("/{agent_id}/make-public")
async def make_agent_public(
    agent_id: str,
    current_user: dict = Depends(get_current_user)
) -> JSONResponse:
    """
    Make an agent public (admin only).
    
    :param agent_id: The ID of the agent to make public.
    :param current_user: Current user from JWT token.
    :return: Success message.
    """
    from ..user.auth import AuthMiddleware
    
    # Check admin privileges
    try:
        AuthMiddleware.require_admin(current_user)
    except Exception:
        return JSONResponse(
            status_code=403,
            content={"error": "Admin privileges required"}
        )
    
    # Make agent public using service method
    success = agent_service.make_agent_public(agent_id)
    
    if success:
        return JSONResponse(
            content={
                "success": True,
                "message": "Agent has been made public successfully"
            }
        )
    else:
        return JSONResponse(
            status_code=404,
            content={"error": "Agent not found or failed to make public"}
        )
