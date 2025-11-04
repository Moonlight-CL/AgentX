from typing import Dict, List
import asyncio

from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from ..orchestration.service import OrchestrationService
from ..orchestration.models import (
    OrchestrationConfig, 
    OrchestrationExecution, 
    ExecutionRequest, 
    ExecutionResponse
)

# Initialize services
orchestration_service = OrchestrationService()

router = APIRouter(
    prefix="/orchestration",
    tags=["orchestration"],
    responses={404: {"description": "Not found"}}
)

@router.post("/create", response_model=OrchestrationConfig)
async def create_orchestration(request: Request) -> OrchestrationConfig:
    """
    Create a new orchestration configuration.
    """
    try:
        data = await request.json()

        print("Received orchestration creation request:", data)
        
        # Get current user from request state (set by AuthMiddleware)
        current_user = getattr(request.state, 'current_user', None)
        user_id = current_user.get('user_id', '') if current_user else ''
        
        return orchestration_service.create_orchestration(data, user_id)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create orchestration: {str(e)}")

@router.get("/list", response_model=List[OrchestrationConfig])
async def list_orchestrations(request: Request) -> List[OrchestrationConfig]:
    """
    List all orchestrations for the current user.
    """
    try:
        # Get current user from request state
        current_user = getattr(request.state, 'current_user', None)
        user_id = current_user.get('user_id', '') if current_user else ''
        
        return orchestration_service.list_orchestrations(user_id)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list orchestrations: {str(e)}")

@router.get("/{orchestration_id}", response_model=OrchestrationConfig)
async def get_orchestration(orchestration_id: str, request: Request) -> OrchestrationConfig:
    """
    Get a specific orchestration by ID.
    """
    try:
        # Get current user from request state
        current_user = getattr(request.state, 'current_user', None)
        user_id = current_user.get('user_id', '') if current_user else ''
        
        orchestration = orchestration_service.get_orchestration(orchestration_id, user_id)
        if not orchestration:
            raise HTTPException(status_code=404, detail="Orchestration not found")
        
        return orchestration
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get orchestration: {str(e)}")

@router.put("/{orchestration_id}", response_model=OrchestrationConfig)
async def update_orchestration(orchestration_id: str, request: Request) -> OrchestrationConfig:
    """
    Update an existing orchestration configuration.
    """
    try:
        data = await request.json()
        
        # Get current user from request state
        current_user = getattr(request.state, 'current_user', None)
        user_id = current_user.get('user_id', '') if current_user else ''
        
        orchestration = orchestration_service.update_orchestration(orchestration_id, data, user_id)
        if not orchestration:
            raise HTTPException(status_code=404, detail="Orchestration not found")
        
        return orchestration
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update orchestration: {str(e)}")

@router.delete("/{orchestration_id}")
async def delete_orchestration(orchestration_id: str, request: Request) -> Dict[str, str]:
    """
    Delete an orchestration configuration.
    """
    try:
        # Get current user from request state
        current_user = getattr(request.state, 'current_user', None)
        user_id = current_user.get('user_id', '') if current_user else ''
        
        success = orchestration_service.delete_orchestration(orchestration_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Orchestration not found")
        
        return {"message": "Orchestration deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete orchestration: {str(e)}")

@router.post("/{orchestration_id}/execute", response_model=ExecutionResponse)
async def execute_orchestration(
    orchestration_id: str, 
    execution_request: ExecutionRequest,
    request: Request,
    background_tasks: BackgroundTasks
) -> ExecutionResponse:
    """
    Execute an orchestration configuration.
    """
    try:
        # Get current user from request state
        current_user = getattr(request.state, 'current_user', None)
        user_id = current_user.get('user_id', '') if current_user else ''
        
        # Create execution using service
        execution = orchestration_service.create_execution(orchestration_id, execution_request, user_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Orchestration not found")
        
        # Get orchestration for background execution
        orchestration = orchestration_service.get_orchestration(orchestration_id, user_id)
        
        # Add background task to execute the orchestration
        background_tasks.add_task(
            execute_orchestration_in_background,
            execution=execution,
            orchestration=orchestration
        )
        
        return ExecutionResponse(
            executionId=execution.id,
            status='pending',
            message='Orchestration execution started'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute orchestration: {str(e)}")

@router.get("/execution/{execution_id}/status", response_model=OrchestrationExecution)
async def get_execution_status(execution_id: str, request: Request) -> OrchestrationExecution:
    """
    Get the status of an orchestration execution.
    """
    try:
        # Get current user from request state
        current_user = getattr(request.state, 'current_user', None)
        user_id = current_user.get('user_id', '') if current_user else ''
        
        execution = orchestration_service.get_execution(execution_id, user_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        return execution
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get execution status: {str(e)}")

@router.post("/execution/{execution_id}/stop")
async def stop_execution(execution_id: str, request: Request) -> Dict[str, str]:
    """
    Stop a running orchestration execution.
    """
    try:
        # Get current user from request state
        current_user = getattr(request.state, 'current_user', None)
        user_id = current_user.get('user_id', '') if current_user else ''
        
        success = orchestration_service.stop_execution(execution_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        return {"message": "Execution stopped successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop execution: {str(e)}")

@router.get("/executions", response_model=List[OrchestrationExecution])
async def list_executions(request: Request, orchestrationId: str = None) -> List[OrchestrationExecution]:
    """
    List executions for the current user, optionally filtered by orchestration ID.
    """
    try:
        # Get current user from request state
        current_user = getattr(request.state, 'current_user', None)
        user_id = current_user.get('user_id', '') if current_user else ''
        
        executions = orchestration_service.list_executions(user_id, orchestrationId)
        return executions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list executions: {str(e)}")

async def execute_orchestration_in_background(
    execution: OrchestrationExecution,
    orchestration: OrchestrationConfig
):
    """
    Execute an orchestration in the background using the service layer with cancellation support.
    """
    try:
        await orchestration_service.execute_orchestration(execution, orchestration)
        print(f"Background execution completed for orchestration {execution.id}")
        
    except asyncio.CancelledError:
        print(f"Background execution cancelled for orchestration {execution.id}")
        
    except Exception as e:
        print(e)
        print(f"Error in background execution for orchestration {execution.id}: {str(e)}")
