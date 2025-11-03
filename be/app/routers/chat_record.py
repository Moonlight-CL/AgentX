from fastapi import APIRouter, Depends
from typing import List

from ..agent.agent import ChatRecord, ChatResponse, ChatRecordService
from ..user.auth import get_current_user

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    responses={404: {"description": "Not found"}}
)

chat_service = ChatRecordService()


# List top 100 Chat Records for current user
@router.get("/list_record")
def list_chats(current_user: dict = Depends(get_current_user)) -> List[ChatRecord]:
    user_id = current_user.get('user_id', 'public')
    return chat_service.get_chat_records_by_user(user_id)

@router.get("/get_chat")
def get_chat(chat_id: str, current_user: dict = Depends(get_current_user)) -> ChatRecord | None:
    user_id = current_user.get('user_id', 'public')
    chat_record = chat_service.get_chat_record(user_id, chat_id)
    return chat_record

@router.get("/list_chat_responses")
def list_chat_responses(chat_id: str, current_user: dict = Depends(get_current_user)) -> List[ChatResponse]:
    
    user_id = current_user.get('user_id', 'public')
    chat_record = chat_service.get_chat_record(user_id, chat_id)
    if chat_record:
        # Use session-based approach to get chat responses
        return chat_service.get_all_chat_responses_from_session(chat_id, chat_record.agent_id)
    return []

# delete chat record
@router.delete("/del_chat")
def del_chat(chat_id: str, current_user: dict = Depends(get_current_user)):

    user_id = current_user.get('user_id', 'public')
    chat_service.del_chat(user_id ,chat_id)
    return {"message": "Chat deleted successfully"}
    # # First verify the chat belongs to the current user
    # chat_record = chat_service.get_chat_record(chat_id)
    # if chat_record and (chat_record.user_id == current_user.get('user_id', '')):
    #     chat_service.del_chat(user_id ,chat_id)
    #     return {"message": "Chat deleted successfully"}
    # return {"error": "Chat not found or Access denied"}
