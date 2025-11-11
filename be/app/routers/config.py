from fastapi import APIRouter, HTTPException, Depends
from ..config.config import ConfigService
from ..config.models import (
    CreateConfigRequest, 
    UpdateConfigRequest,
    ConfigResponse,
    ConfigListResponse,
    CategoryTreeResponse,
    ModelProviderRequest
)
from ..user.auth import get_current_user

router = APIRouter(prefix="/config", tags=["config"])

# Initialize config service
config_service = ConfigService()

@router.post("/create", response_model=ConfigResponse)
async def create_config(
    config_request: CreateConfigRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new system configuration.
    """
    try:
        config = config_service.create_config(config_request)
        return ConfigResponse(
            success=True,
            message="Configuration created successfully",
            data=config
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create configuration: {str(e)}")

@router.get("/get/{key}", response_model=ConfigResponse)
async def get_config(
    key: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific configuration by key.
    """
    try:
        config = config_service.get_config(key)
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        return ConfigResponse(
            success=True,
            message="Configuration retrieved successfully",
            data=config
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {str(e)}")

@router.put("/update/{key}", response_model=ConfigResponse)
async def update_config(
    key: str,
    update_request: UpdateConfigRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing configuration.
    """
    try:
        config = config_service.update_config(key, update_request)
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        return ConfigResponse(
            success=True,
            message="Configuration updated successfully",
            data=config
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")

@router.delete("/delete/{key}")
async def delete_config(
    key: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a configuration.
    """
    try:
        success = config_service.delete_config(key)
        if not success:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        return {"success": True, "message": "Configuration deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete configuration: {str(e)}")

@router.get("/list", response_model=ConfigListResponse)
async def list_all_configs(
    current_user: dict = Depends(get_current_user)
):
    """
    List all configurations.
    """
    try:
        configs = config_service.list_all_configs()
        return ConfigListResponse(
            success=True,
            message="Configurations retrieved successfully",
            data=configs
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list configurations: {str(e)}")

@router.get("/list/{parent}", response_model=ConfigListResponse)
async def list_configs_by_parent(
    parent: str,
    current_user: dict = Depends(get_current_user)
):
    """
    List all configurations under a specific parent.
    """
    try:
        configs = config_service.list_configs_by_parent(parent)
        return ConfigListResponse(
            success=True,
            message=f"Configurations for parent '{parent}' retrieved successfully",
            data=configs
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list configurations for parent: {str(e)}")

@router.get("/root-categories", response_model=ConfigListResponse)
async def get_root_categories(
    current_user: dict = Depends(get_current_user)
):
    """
    Get all root categories.
    """
    try:
        categories = config_service.get_root_categories()
        return ConfigListResponse(
            success=True,
            message="Root categories retrieved successfully",
            data=categories
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get root categories: {str(e)}")

@router.get("/category-tree", response_model=CategoryTreeResponse)
async def get_category_tree(
    current_user: dict = Depends(get_current_user)
):
    """
    Get the configuration category tree structure.
    """
    try:
        tree = config_service.get_category_tree()
        return CategoryTreeResponse(
            success=True,
            message="Category tree retrieved successfully",
            data=tree
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get category tree: {str(e)}")

@router.post("/model-provider", response_model=ConfigResponse)
async def create_model_provider(
    provider_request: ModelProviderRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a model provider category and configuration.
    """
    try:
        # First create the provider category
        category = config_service.create_model_provider_category(
            provider_request.provider_key,
            provider_request.provider_display_name
        )
        
        # Then create the configuration item
        config_data = provider_request.config.model_dump()
        config = config_service.create_model_provider_config(
            provider_request.provider_key,
            "default",
            config_data
        )
        
        return ConfigResponse(
            success=True,
            message="Model provider created successfully",
            data=config
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create model provider: {str(e)}")

@router.post("/init-default-categories")
async def init_default_categories(
    current_user: dict = Depends(get_current_user)
):
    """
    Initialize default configuration categories.
    """
    try:
        # Create model_providers root category
        model_providers_request = CreateConfigRequest(
            key="model_providers",
            value="{}",
            key_display_name="模型提供商",
            type="category",
            seq_num=1
        )
        config_service.create_config(model_providers_request)

        # Create user_groups root category
        user_groups_request = CreateConfigRequest(
            key="user_groups",
            value="{}",
            key_display_name="用户组",
            type="category",
            seq_num=2
        )
        config_service.create_config(user_groups_request)

        providers = ["Bedrock", "OpenAI", "Anthropic", "LiteLLM"]
        for idx, provider in enumerate(providers):
            conf = CreateConfigRequest(
                key=provider,
                value=f'{{ "val": {idx+1} }}',
                key_display_name=provider,
                type="category",
                seq_num= idx * 5, 
                parent= "model_providers"
            )   
            config_service.create_config(conf)

        bedrock_models = [("claude-3.7-sonnet-us", "us.anthropic.claude-3-7-sonnet-20250219-v1:0"),
                          ("claude-4.0-sonnet-us", "us.anthropic.claude-sonnet-4-20250514-v1:0"),
                          ("claude-4.5-sonnet-us", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"),
                          ("qwen3-coder-480b", "qwen.qwen3-coder-480b-a35b-v1:0")
                          ]
        for idx, (m_key, m_id) in enumerate(bedrock_models):
            conf = CreateConfigRequest(
                key=m_key,
                value=f'{{ "model_id": "{m_id}" }}',
                key_display_name=m_key,
                type="item",
                seq_num= idx * 5, 
                parent= "Bedrock"
            )
            config_service.create_config(conf)
        
        return {"success": True, "message": "Default categories initialized successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize default categories: {str(e)}")
