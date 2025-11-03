
from fastapi import APIRouter, Request, Depends

from ..mcp.mcp import HttpMCPServer, MCPService
from ..user.auth import get_current_user


mcp_service = MCPService()

router = APIRouter(
    prefix="/mcp",
    tags=["mcp"],
    responses={404: {"description": "Not found"}}
)


@router.get("/list")
def list_mcp_servers(current_user: dict = Depends(get_current_user)) -> list[HttpMCPServer]:
    """
    List all MCP servers for the current user.
    :return: A list of MCP servers.
    """
    user_id = current_user.get('user_id', 'public')
    return mcp_service.list_mcp_servers(user_id)

@router.get("/get/{server_id}")
def get_mcp_server(server_id: str, current_user: dict = Depends(get_current_user)) -> HttpMCPServer | None:
    """
    Get a specific MCP server by ID.
    :param server_id: The ID of the MCP server to retrieve.
    :return: Details of the specified MCP server.
    """
    user_id = current_user.get('user_id', 'public')
    server = mcp_service.get_mcp_server(user_id, server_id)
    if not server:
        raise ValueError(f"MCP server with ID {server_id} not found.")
    return server

@router.delete("/delete/{server_id}")
def delete_mcp_server(server_id: str, current_user: dict = Depends(get_current_user)) -> bool:
    """
    Delete a specific MCP server by ID.
    :param server_id: The ID of the MCP server to delete.
    :return: True if deletion was successful, False otherwise.
    """
    user_id = current_user.get('user_id', 'public')
    return mcp_service.delete_mcp_server(user_id, server_id)

@router.post("/createOrUpdate")
async def create_mcp_server(server: Request, current_user: dict = Depends(get_current_user)) -> HttpMCPServer:
    """
    Create or update an MCP server.
    :param server: The MCP server data to create or update.
    :return: Confirmation of MCP server creation or update.
    """
    user_id = current_user.get('user_id', 'public')
    server_data = await server.json()
    
    # If updating existing server, delete the old one first
    if server_data.get("id"):
        mcp_service.delete_mcp_server(user_id, server_data["id"])
    
    server = HttpMCPServer(
        id=server_data.get("id"),
        name=server_data.get("name"),
        desc=server_data.get("desc"),
        host=server_data.get("host")
    )
    mcp_service.add_mcp_server(server, user_id)
    return server
