from fastapi import APIRouter, Request, HTTPException, Depends
from typing import List, Dict, Any

from ..schedule import Schedule, list_schedules, create_schedule, update_schedule, delete_schedule
from ..user.auth import get_current_user

# Router definition
router = APIRouter(
    prefix="/schedule",
    tags=["schedule"],
    responses={404: {"description": "Not found"}}
)

@router.get("/list", response_model=List[Schedule])
async def get_schedules(current_user: dict = Depends(get_current_user)) -> List[Schedule]:
    """
    List all agent schedules for the current user.
    :return: A list of schedules.
    """
    user_id = current_user.get("user_id")
    return list_schedules(user_id)

@router.post("/create", response_model=Schedule)
async def create_schedule_endpoint(request: Request, current_user: dict = Depends(get_current_user)) -> Schedule:
    """
    Create a new agent schedule.
    :param request: The request containing the schedule data.
    :return: The created schedule.
    """
    try:
        data = await request.json()
        user_id = current_user.get("user_id")
        agent_id = data.get("agentId")
        agent_user_id = data.get("agentUserId")
        cron_expression = data.get("cronExpression")
        user_message = data.get("user_message", f"[Scheduled Task] Execute scheduled task for agent {agent_id}")
        
        if not agent_id or not cron_expression:
            raise HTTPException(status_code=400, detail="Agent ID and cron expression are required")
        
        if not agent_user_id:
            raise HTTPException(status_code=400, detail="Agent User ID is required")
        
        schedule_item = create_schedule(agent_id, user_id, agent_user_id, cron_expression, user_message)
        
        return Schedule(
            user_id=schedule_item["user_id"],
            id=schedule_item["id"],
            agentId=schedule_item["agentId"],
            agentUserId=schedule_item.get("agentUserId"),
            agentName=schedule_item["agentName"],
            cronExpression=schedule_item["cronExpression"],
            status=schedule_item["status"],
            createdAt=schedule_item["createdAt"],
            updatedAt=schedule_item["updatedAt"],
            user_message=schedule_item.get("user_message")
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")

@router.put("/update/{schedule_id}")
async def update_schedule_endpoint(schedule_id: str, request: Request, current_user: dict = Depends(get_current_user)) -> Schedule:
    """
    Update a specific schedule by ID.
    :param schedule_id: The ID of the schedule to update.
    :param request: The request containing the updated schedule data.
    :return: The updated schedule.
    """
    try:
        data = await request.json()
        user_id = current_user.get("user_id")
        agent_id = data.get("agentId")
        agent_user_id = data.get("agentUserId")
        cron_expression = data.get("cronExpression")
        user_message = data.get("user_message", f"[Scheduled Task] Execute scheduled task for agent {agent_id}")
        
        if not agent_id or not cron_expression:
            raise HTTPException(status_code=400, detail="Agent ID and cron expression are required")
        
        if not agent_user_id:
            raise HTTPException(status_code=400, detail="Agent User ID is required")
        
        updated_schedule = update_schedule(schedule_id, user_id, agent_id, agent_user_id, cron_expression, user_message)
        
        return Schedule(
            user_id=updated_schedule["user_id"],
            id=updated_schedule["id"],
            agentId=updated_schedule["agentId"],
            agentUserId=updated_schedule.get("agentUserId"),
            agentName=updated_schedule["agentName"],
            cronExpression=updated_schedule["cronExpression"],
            status=updated_schedule["status"],
            createdAt=updated_schedule["createdAt"],
            updatedAt=updated_schedule["updatedAt"],
            user_message=updated_schedule.get("user_message")
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {str(e)}")

@router.delete("/delete/{schedule_id}")
async def remove_schedule(schedule_id: str, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Delete a specific schedule by ID.
    :param schedule_id: The ID of the schedule to delete.
    :return: Confirmation of deletion.
    """
    user_id = current_user.get("user_id")
    return delete_schedule(schedule_id, user_id)
