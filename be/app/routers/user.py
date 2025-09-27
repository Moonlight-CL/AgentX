from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from typing import List
from ..user.models import User, UserCreate, UserLogin, UserUpdate, UserService
from ..user.auth import JWTAuth, get_current_user, AuthMiddleware

router = APIRouter(
    prefix="/user",
    tags=["user"],
    responses={404: {"description": "Not found"}}
)

user_service = UserService()

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
                "last_login": user.last_login
            },
            "access_token": access_token,
            "token_type": "bearer"
        }
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
    current_user: dict = Depends(AuthMiddleware.require_admin)
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
