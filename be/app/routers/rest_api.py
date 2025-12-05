from fastapi import APIRouter, HTTPException, Depends
from typing import List
import uuid

from app.models.rest_api import (
    RestAPICreate, RestAPIUpdate, RestAPIResponse, TestEndpointRequest
)
from app.services.rest_api_registry import RestAPIRegistry
from app.services.rest_mcp_adapter import RestMCPAdapter
from app.user.auth import get_current_user

router = APIRouter(prefix="/rest-apis", tags=["rest-apis"])
registry = RestAPIRegistry()


@router.post("", response_model=RestAPIResponse)
async def create_rest_api(
    config: RestAPICreate,
    current_user: dict = Depends(get_current_user)
):
    """Register a new REST API"""
    user_id = current_user.get('user_id', 'public')
    api_id = str(uuid.uuid4())
    item = await registry.create_api(user_id, api_id, config.model_dump())
    return RestAPIResponse(api_id=api_id, user_id=user_id, **config.model_dump())


@router.get("", response_model=List[RestAPIResponse])
async def list_rest_apis(current_user: dict = Depends(get_current_user)):
    """List user's registered REST APIs"""
    user_id = current_user.get('user_id', 'public')
    apis = await registry.get_user_apis(user_id)
    return [RestAPIResponse(**api) for api in apis]


@router.get("/{api_id}", response_model=RestAPIResponse)
async def get_rest_api(
    api_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific REST API"""
    user_id = current_user.get('user_id', 'public')
    api = await registry.get_api(user_id, api_id)
    if not api:
        raise HTTPException(status_code=404, detail="REST API not found")
    return RestAPIResponse(**api)


@router.put("/{api_id}", response_model=RestAPIResponse)
async def update_rest_api(
    api_id: str,
    config: RestAPIUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update REST API configuration"""
    user_id = current_user.get('user_id', 'public')
    existing = await registry.get_api(user_id, api_id)
    if not existing:
        raise HTTPException(status_code=404, detail="REST API not found")
    
    item = await registry.update_api(user_id, api_id, config.model_dump())
    return RestAPIResponse(api_id=api_id, user_id=user_id, **config.model_dump())


@router.delete("/{api_id}")
async def delete_rest_api(
    api_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete REST API"""
    user_id = current_user.get('user_id', 'public')
    existing = await registry.get_api(user_id, api_id)
    if not existing:
        raise HTTPException(status_code=404, detail="REST API not found")
    
    await registry.delete_api(user_id, api_id)
    return {"message": "REST API deleted successfully"}


@router.post("/{api_id}/test")
async def test_endpoint(
    api_id: str,
    request: TestEndpointRequest,
    current_user: dict = Depends(get_current_user)
):
    """Test an endpoint before saving"""
    user_id = current_user.get('user_id', 'public')
    api = await registry.get_api(user_id, api_id)
    if not api:
        raise HTTPException(status_code=404, detail="REST API not found")
    
    endpoint = next(
        (e for e in api.get('endpoints', []) if e['path'] == request.endpoint_path),
        None
    )
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    adapter = RestMCPAdapter(registry)
    try:
        result = await adapter._execute_request(api, endpoint, request.params or {})
        return {"success": True, "response": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await adapter.close()
