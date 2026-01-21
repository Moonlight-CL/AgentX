from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import os

from .routers import agent
from .routers import mcp
from .routers import chat_record
from .routers import schedule
from .routers import user
from .routers import orchestration
from .routers import config
from .routers import files
from .routers import rest_api
from .middleware.auth_middleware import AuthMiddleware, AuthConfig
from .routers.agentcore_handler import AgentCoreInvocationHandler

app = FastAPI()

# Add authentication middleware
app.add_middleware(AuthMiddleware, public_paths=AuthConfig.get_public_paths())

# Read APP_ENV environment variable and set URL prefix accordingly
app_env = os.environ.get("APP_ENV", "")
url_prefix = "/api" if app_env == "production" else ""

app.include_router(agent.router, prefix=url_prefix)
app.include_router(mcp.router, prefix=url_prefix)
app.include_router(chat_record.router, prefix=url_prefix)
app.include_router(schedule.router, prefix=url_prefix)
app.include_router(user.router, prefix=url_prefix)
app.include_router(orchestration.router, prefix=url_prefix)
app.include_router(config.router, prefix=url_prefix)
app.include_router(files.router, prefix=url_prefix)
app.include_router(rest_api.router, prefix=url_prefix)

@app.get("/")
def home():
    return {"App": "AgentX-BE"}

# AgentCore Runtime endpoints
@app.get("/ping")
async def ping():
    """
    Health check endpoint required by AgentCore Runtime.
    Returns 200 OK when the service is healthy.
    """
    return {"status": "healthy", "service": "AgentX-BE"}

@app.post("/invocations")
async def invocations(request: Request):
    """
    Main invocation endpoint required by AgentCore Runtime.
    This endpoint processes agent requests and returns streaming responses using SSE.

    Expected input format:
    {
        "input": {
            "agent_id": "agent_id",
            "prompt": "user message",
            "session_id": "optional_session_id",
            "user_id": "optional_user_id",
            "file_attachments": [],  # optional
            "chat_record_enabled": true,  # optional, default True
            "use_s3_reference": false,  # optional, default False
            "agent_owner_id": "optional_owner_id"  # optional
        }
    }
    """
    try:
        # Parse request body
        data = await request.json()

        # Use handler to process invocation
        handler = AgentCoreInvocationHandler()

        # Return streaming response
        return StreamingResponse(
            handler.handle_invocation_stream(data),
            media_type="text/event-stream"
        )

    except Exception as e:
        print(f"Error processing invocation: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Agent processing failed: {str(e)}"
            }
        )
