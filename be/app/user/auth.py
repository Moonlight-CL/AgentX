import jwt
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .models import TokenData, UserService

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days

security = HTTPBearer()
user_service = UserService()

class JWTAuth:
    """JWT Authentication utilities."""
    
    @staticmethod
    def create_access_token(user_id: str, username: str) -> str:
        """
        Create a JWT access token.
        
        :param user_id: The user ID.
        :param username: The username.
        :return: JWT token string.
        """
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = {
            "user_id": user_id,
            "username": username,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[TokenData]:
        """
        Verify and decode a JWT token.
        
        :param token: The JWT token to verify.
        :return: TokenData if valid, None otherwise.
        """
        try:
            # Decode and verify the token (this automatically checks expiration)
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("user_id")
            username: str = payload.get("username")
            exp_timestamp = payload.get("exp")
            
            if user_id is None or username is None or exp_timestamp is None:
                return None
            
            # Convert timestamp to datetime
            exp: datetime = datetime.fromtimestamp(exp_timestamp)
            
            # Additional check: ensure token hasn't expired (jwt.decode should handle this, but double-check)
            if datetime.utcnow() > exp:
                return None
            
            return TokenData(user_id=user_id, username=username, exp=exp)
        except jwt.ExpiredSignatureError:
            # Token has expired
            return None
        except jwt.InvalidTokenError:
            # Token is invalid (malformed, wrong signature, etc.)
            return None
        except Exception:
            # Any other error
            return None
    
    @staticmethod
    def get_current_user_from_token(token: str) -> Optional[dict]:
        """
        Get current user information from JWT token.
        
        :param token: The JWT token.
        :return: User information dict if valid, None otherwise.
        """
        token_data = JWTAuth.verify_token(token)
        if not token_data:
            return None
        
        # Verify user still exists and is active
        user = user_service.get_user_by_id(token_data.user_id)
        if not user or user.status.value != "active":
            return None
        
        return {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "status": user.status.value,
            "is_admin": user.is_admin,
            "user_groups": user.user_groups or []
        }

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    FastAPI dependency to get current authenticated user.
    
    :param credentials: HTTP Bearer credentials.
    :return: Current user information.
    :raises HTTPException: If authentication fails.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    user = JWTAuth.get_current_user_from_token(credentials.credentials)
    if user is None:
        raise credentials_exception
    
    return user

def get_optional_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
    """
    FastAPI dependency to get current authenticated user (optional).
    
    :param credentials: HTTP Bearer credentials (optional).
    :return: Current user information if authenticated, None otherwise.
    """
    if not credentials:
        return None
    
    return JWTAuth.get_current_user_from_token(credentials.credentials)

class AuthMiddleware:
    """Authentication middleware for protecting routes."""
    
    @staticmethod
    def require_auth(user: dict = Depends(get_current_user)) -> dict:
        """
        Require authentication for a route.
        
        :param user: Current user from dependency.
        :return: Current user information.
        """
        return user
    
    @staticmethod
    def require_admin(user: dict = Depends(get_current_user)) -> dict:
        """
        Require admin privileges for a route.
        
        :param user: Current user from dependency.
        :return: Current user information.
        :raises HTTPException: If user is not admin.
        """
        if not user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        return user
