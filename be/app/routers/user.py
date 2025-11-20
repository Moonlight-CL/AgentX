from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from typing import List
from pydantic import BaseModel
from ..user.models import User, UserCreate, UserLogin, UserUpdate, UserService
from ..user.auth import JWTAuth, get_current_user, AuthMiddleware
from ..user.azure_auth import azure_auth
from ..config.config import ConfigService

router = APIRouter(
    prefix="/user",
    tags=["user"],
    responses={404: {"description": "Not found"}}
)

user_service = UserService()
config_service = ConfigService()

class AzureLoginRequest(BaseModel):
    access_token: str
    id_token: str

class AzureTokenValidationRequest(BaseModel):
    access_token: str

@router.post("/register")
async def register_user(user_data: UserCreate) -> JSONResponse:
    """
    Register a new user.
    
    :param user_data: User registration data.
    :return: Success message with user info.
    """
    try:
        user = user_service.create_user(user_data)
        
        # Create JWT token
        access_token = JWTAuth.create_access_token(user.user_id, user.username)
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "User registered successfully",
                "user": {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "status": user.status.value,
                    "created_at": user.created_at
                },
                "access_token": access_token,
                "token_type": "bearer"
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user"
        )

@router.post("/login")
async def login_user(login_data: UserLogin) -> JSONResponse:
    """
    Authenticate user and return JWT token.
    
    :param login_data: User login credentials.
    :return: JWT token and user info.
    """
    user = user_service.authenticate_user(login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create JWT token
    access_token = JWTAuth.create_access_token(user.user_id, user.username)
    
    return JSONResponse(
        content={
            "message": "Login successful",
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "status": user.status.value,
                "last_login": user.last_login,
                "auth_provider": user.auth_provider.value,
                "display_name": user.display_name
            },
            "access_token": access_token,
            "token_type": "bearer"
        }
    )

@router.post("/azure-login")
async def azure_login(azure_data: AzureLoginRequest) -> JSONResponse:
    """
    Authenticate user with Azure AD tokens and return local JWT token.
    
    :param azure_data: Azure AD tokens (access_token and id_token).
    :return: Local JWT token and user info.
    """
    try:
        # Verify Azure AD ID token
        azure_user_info = azure_auth.verify_azure_token(azure_data.id_token)
        print(azure_user_info)
        
        if not azure_user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Azure AD token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Find or create user based on Azure AD info
        user = user_service.get_user_by_azure_object_id(azure_user_info["azure_object_id"])
        
        if not user:
            # Create new user from Azure AD info
            user = user_service.create_azure_user(azure_user_info)
        else:
            # Update existing user with latest Azure AD info
            user = user_service.update_azure_user(user.user_id, azure_user_info)
        
        # Update last login
        user_service.update_last_login(user.user_id)
        
        # Create local JWT token
        access_token = JWTAuth.create_access_token(user.user_id, user.username)
        
        return JSONResponse(
            content={
                "message": "Azure AD login successful",
                "user": {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "status": user.status.value,
                    "last_login": user.last_login,
                    "auth_provider": user.auth_provider.value,
                    "display_name": user.display_name,
                    "azure_object_id": user.azure_object_id
                },
                "access_token": access_token,
                "token_type": "bearer"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Azure AD login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Azure AD login failed"
        )

@router.post("/azure-validate")
async def validate_azure_token(token_data: AzureTokenValidationRequest) -> JSONResponse:
    """
    Validate Azure AD access token and return user info.
    
    :param token_data: Azure AD access token.
    :return: User information if token is valid.
    """
    try:
        # Verify Azure AD access token
        azure_user_info = azure_auth.verify_azure_token(token_data.access_token)
        
        if not azure_user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Azure AD token"
            )
        
        # Find user based on Azure AD info
        user = user_service.get_user_by_azure_object_id(azure_user_info["azure_object_id"])
        
        if not user:
            return JSONResponse(
                content={
                    "valid": True,
                    "user_exists": False,
                    "azure_user_info": {
                        "azure_object_id": azure_user_info["azure_object_id"],
                        "email": azure_user_info["email"],
                        "name": azure_user_info["name"],
                        "given_name": azure_user_info["given_name"],
                        "family_name": azure_user_info["family_name"]
                    }
                }
            )
        
        return JSONResponse(
            content={
                "valid": True,
                "user_exists": True,
                "user": {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "status": user.status.value,
                    "auth_provider": user.auth_provider.value,
                    "display_name": user.display_name
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Azure AD token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token validation failed"
        )

@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Get current authenticated user information.
    
    :param current_user: Current user from JWT token.
    :return: User information.
    """
    return {
        "user": current_user
    }

@router.put("/me")
async def update_current_user(
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
) -> JSONResponse:
    """
    Update current user information.
    
    :param user_data: User update data.
    :param current_user: Current user from JWT token.
    :return: Updated user information.
    """
    updated_user = user_service.update_user(current_user["user_id"], user_data)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return JSONResponse(
        content={
            "message": "User updated successfully",
            "user": {
                "user_id": updated_user.user_id,
                "username": updated_user.username,
                "email": updated_user.email,
                "status": updated_user.status.value,
                "updated_at": updated_user.updated_at
            }
        }
    )

@router.post("/change-password")
async def change_password(
    password_data: dict,
    current_user: dict = Depends(get_current_user)
) -> JSONResponse:
    """
    Change user password.
    
    :param password_data: Dictionary with old_password and new_password.
    :param current_user: Current user from JWT token.
    :return: Success message.
    """
    old_password = password_data.get("old_password")
    new_password = password_data.get("new_password")
    
    if not old_password or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both old_password and new_password are required"
        )
    
    success = user_service.change_password(
        current_user["user_id"],
        old_password,
        new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to change password. Please check your current password."
        )
    
    return JSONResponse(
        content={
            "message": "Password changed successfully"
        }
    )

@router.post("/logout")
async def logout_user(current_user: dict = Depends(get_current_user)) -> JSONResponse:
    """
    Logout user (client should discard the token).
    
    :param current_user: Current user from JWT token.
    :return: Success message.
    """
    return JSONResponse(
        content={
            "message": "Logout successful"
        }
    )

@router.get("/verify-token")
async def verify_token(current_user: dict = Depends(get_current_user)) -> JSONResponse:
    """
    Verify if the current token is valid.
    
    :param current_user: Current user from JWT token.
    :return: Token validity status.
    """
    return JSONResponse(
        content={
            "valid": True,
            "user": current_user
        }
    )

# Admin endpoints (require authentication)
@router.get("/list")
async def list_users(
    limit: int = 100,
    current_user: dict = Depends(AuthMiddleware.require_auth)
) -> List[dict]:
    """
    List all users (admin only).
    
    :param limit: Maximum number of users to return.
    :param current_user: Current admin user.
    :return: List of users.
    """
    users = user_service.list_users(limit)
    
    return [
        {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "status": user.status.value,
            "is_admin": user.is_admin,
            "user_groups": user.user_groups or [],
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "last_login": user.last_login
        }
        for user in users
    ]

@router.get("/{user_id}")
async def get_user_by_id(
    user_id: str,
    current_user: dict = Depends(AuthMiddleware.require_admin)
) -> dict:
    """
    Get user by ID (admin only).
    
    :param user_id: User ID to retrieve.
    :param current_user: Current admin user.
    :return: User information.
    """
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "status": user.status.value,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "last_login": user.last_login
        }
    }

@router.put("/{user_id}")
async def update_user_by_id(
    user_id: str,
    user_data: UserUpdate,
    current_user: dict = Depends(AuthMiddleware.require_admin)
) -> JSONResponse:
    """
    Update user by ID (admin only).
    
    :param user_id: User ID to update.
    :param user_data: User update data.
    :param current_user: Current admin user.
    :return: Updated user information.
    """
    updated_user = user_service.update_user(user_id, user_data)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return JSONResponse(
        content={
            "message": "User updated successfully",
            "user": {
                "user_id": updated_user.user_id,
                "username": updated_user.username,
                "email": updated_user.email,
                "status": updated_user.status.value,
                "updated_at": updated_user.updated_at
            }
        }
    )

@router.delete("/{user_id}")
async def delete_user_by_id(
    user_id: str,
    current_user: dict = Depends(AuthMiddleware.require_admin)
) -> JSONResponse:
    """
    Delete user by ID (admin only).
    
    :param user_id: User ID to delete.
    :param current_user: Current admin user.
    :return: Success message.
    """
    # Prevent self-deletion
    if user_id == current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    success = user_service.delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or failed to delete"
        )
    
    return JSONResponse(
        content={
            "message": "User deleted successfully"
        }
    )

# User group management endpoints (admin only)
@router.get("/groups/list")
async def list_user_groups(
    current_user: dict = Depends(AuthMiddleware.require_auth)
) -> JSONResponse:
    """
    List all user groups (admin only).
    
    :param current_user: Current admin user.
    :return: List of user groups.
    """
    try:
        groups = config_service.list_configs_by_parent("user_groups")
        return JSONResponse(
            content={
                "success": True,
                "message": "User groups retrieved successfully",
                "data": [
                    {
                        "id": group.key,
                        "name": group.key_display_name or group.key,
                        "description": group.value,
                        "group_key": group.key[4:] if group.key.startswith("ugs_") else group.key  # Remove ugs_ prefix
                    }
                    for group in groups
                ]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list user groups: {str(e)}")

@router.post("/groups/create")
async def create_user_group(
    group_data: dict,
    current_user: dict = Depends(AuthMiddleware.require_admin)
) -> JSONResponse:
    """
    Create a new user group (admin only).
    
    :param group_data: Group creation data with 'name', 'group_key' and optional 'description'.
    :param current_user: Current admin user.
    :return: Success message.
    """
    try:
        from ..config.models import CreateConfigRequest
        import re
        
        group_name = group_data.get("name")
        group_key = group_data.get("group_key")
        group_description = group_data.get("description", "")
        
        if not group_name:
            raise HTTPException(status_code=400, detail="Group name is required")
        
        if not group_key:
            raise HTTPException(status_code=400, detail="Group key is required")
        
        # Validate group key format (only letters, numbers, underscores)
        if not re.match(r'^[a-zA-Z0-9_]+$', group_key):
            raise HTTPException(
                status_code=400, 
                detail="Group key can only contain letters, numbers, and underscores"
            )
        
        # Add ugs_ prefix to group key
        full_group_key = f"ugs_{group_key}"
        
        # Check if group key already exists
        existing_config = config_service.get_config(full_group_key)
        if existing_config:
            raise HTTPException(status_code=400, detail="Group key already exists")
        
        # Create group configuration
        group_request = CreateConfigRequest(
            key=full_group_key,
            value=group_description,
            key_display_name=group_name,
            type="item",
            parent="user_groups"
        )
        
        config = config_service.create_config(group_request)
        
        return JSONResponse(
            content={
                "success": True,
                "message": "User group created successfully",
                "data": {
                    "id": config.key,
                    "name": config.key_display_name,
                    "description": config.value,
                    "group_key": group_key  # Return the key without prefix for display
                }
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create user group: {str(e)}")

@router.put("/groups/{group_id}")
async def update_user_group(
    group_id: str,
    group_data: dict,
    current_user: dict = Depends(AuthMiddleware.require_admin)
) -> JSONResponse:
    """
    Update a user group (admin only).
    
    :param group_id: Group ID to update.
    :param group_data: Group update data.
    :param current_user: Current admin user.
    :return: Success message.
    """
    try:
        from ..config.models import UpdateConfigRequest
        
        update_request = UpdateConfigRequest(
            value=group_data.get("description"),
            key_display_name=group_data.get("name")
        )
        
        config = config_service.update_config(group_id, update_request)
        if not config:
            raise HTTPException(status_code=404, detail="User group not found")
        
        return JSONResponse(
            content={
                "success": True,
                "message": "User group updated successfully",
                "data": {
                    "id": config.key,
                    "name": config.key_display_name,
                    "description": config.value
                }
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update user group: {str(e)}")

@router.delete("/groups/{group_id}")
async def delete_user_group(
    group_id: str,
    current_user: dict = Depends(AuthMiddleware.require_admin)
) -> JSONResponse:
    """
    Delete a user group (admin only).
    
    :param group_id: Group ID to delete.
    :param current_user: Current admin user.
    :return: Success message.
    """
    try:
        success = config_service.delete_config(group_id)
        if not success:
            raise HTTPException(status_code=404, detail="User group not found")
        
        return JSONResponse(
            content={
                "success": True,
                "message": "User group deleted successfully"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete user group: {str(e)}")

@router.post("/{user_id}/groups")
async def assign_user_to_groups(
    user_id: str,
    group_data: dict,
    current_user: dict = Depends(AuthMiddleware.require_admin)
) -> JSONResponse:
    """
    Assign user to groups (admin only).
    
    :param user_id: User ID to assign groups to.
    :param group_data: Dictionary with 'group_ids' list.
    :param current_user: Current admin user.
    :return: Success message.
    """
    try:
        group_ids = group_data.get("group_ids", [])
        
        user_update = UserUpdate(user_groups=group_ids)
        updated_user = user_service.update_user(user_id, user_update)
        
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return JSONResponse(
            content={
                "success": True,
                "message": "User groups updated successfully",
                "data": {
                    "user_id": updated_user.user_id,
                    "username": updated_user.username,
                    "user_groups": updated_user.user_groups or []
                }
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign user to groups: {str(e)}")
