import os
import json
from typing import Optional, Set
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from ..user.auth import JWTAuth

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Global authentication middleware for FastAPI.
    Validates JWT tokens for all requests except public paths.
    """
    
    def __init__(self, app, public_paths: Optional[Set[str]] = None):
        super().__init__(app)
        
        # Default public paths that don't require authentication
        self.public_paths = public_paths or {
            "/",
            "/user/register",
            "/user/login",
        }
        
        # Add API prefix for production environment
        app_env = os.environ.get("APP_ENV", "")
        if app_env == "production":
            # Add /api prefix versions of public paths
            api_public_paths = {f"/api{path}" for path in self.public_paths}
            self.public_paths.update(api_public_paths)
    
    async def dispatch(self, request: Request, call_next):
        """
        Process each request and validate authentication if required.
        """
        # Get the request path
        path = request.url.path
        
        # Skip authentication for public paths
        if self._is_public_path(path):
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Extract and validate token
        token = self._extract_token(request)
        if not token:
            return self._create_auth_error_response("Missing authentication token")
        
        # Validate token and get user info
        try:
            user_info = JWTAuth.get_current_user_from_token(token)
            if not user_info:
                return self._create_auth_error_response("Invalid or expired token")
            
            # Add user info to request state for use in route handlers
            request.state.current_user = user_info
            
        except Exception as e:
            # Log the error for debugging (in production, you might want to use proper logging)
            print(f"Token validation error: {str(e)}")
            return self._create_auth_error_response("Token validation failed")
        
        # Continue with the request
        response = await call_next(request)
        return response
    
    def _is_public_path(self, path: str) -> bool:
        """
        Check if the given path is in the public paths list.
        """
        # Exact match
        if path in self.public_paths:
            return True
        
        # Check for path patterns (e.g., static files)
        if path.startswith("/static/") or path.startswith("/assets/"):
            return True
        
        return False
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from Authorization header.
        """
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None
        
        # Check for Bearer token format
        if not authorization.startswith("Bearer "):
            return None
        
        # Extract token (remove "Bearer " prefix)
        token = authorization[7:]  # len("Bearer ") = 7
        return token if token else None
    
    def _create_auth_error_response(self, detail: str) -> JSONResponse:
        """
        Create a standardized authentication error response.
        """
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": detail,
                "error_code": "AUTHENTICATION_REQUIRED"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

class AuthConfig:
    """
    Configuration class for authentication middleware.
    """
    
    @staticmethod
    def get_public_paths() -> Set[str]:
        """
        Get the list of public paths that don't require authentication.
        Can be extended or configured via environment variables.
        """
        default_paths = {
            "/",
            "/docs",
            "/openapi.json", 
            "/redoc",
            "/user/register",
            "/user/login",
            "/health",  # Health check endpoint
            "/metrics", # Metrics endpoint (if added)
        }
        
        # Allow configuration via environment variable
        env_paths = os.environ.get("AUTH_PUBLIC_PATHS")
        if env_paths:
            try:
                additional_paths = set(json.loads(env_paths))
                default_paths.update(additional_paths)
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, use default paths
                pass
        
        return default_paths

def create_auth_middleware(app):
    """
    Factory function to create and configure the authentication middleware.
    """
    public_paths = AuthConfig.get_public_paths()
    return AuthMiddleware(app, public_paths)
