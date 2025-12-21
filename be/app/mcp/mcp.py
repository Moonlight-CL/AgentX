
import uuid
import boto3
from pydantic import BaseModel
from ..utils.aws_config import get_aws_region, get_dynamodb_resource, get_http_mcp_table

class HttpMCPServer(BaseModel):
   id: str | None = None
   name: str
   desc: str
   host: str
   headers: dict[str, str] | None = None
   # OAuth Client Credentials Flow fields
   client_id: str | None = None
   client_secret: str | None = None
   token_url: str | None = None


class MCPService:

    dynamodb_table_name = "HttpMCPTable"

    def __init__(self):
        self.dynamodb = get_dynamodb_resource()
        self.mcp_table = get_http_mcp_table()

    def add_mcp_server(self, server: HttpMCPServer, user_id: str = 'public'):
        """
        Add an MCP server to Amazon DynamoDB.

        :param server: The HttpMCPServer object to add.
        :param user_id: The user ID for data isolation.
        :return: None
        """
        if not server.id:
            server.id = uuid.uuid4().hex
        item = {
            'user_id': user_id,
            'id': server.id,
            'name': server.name,
            'desc': server.desc,
            'host': server.host
        }
        if server.headers:
            item['headers'] = server.headers
        # Add OAuth fields if present
        if server.client_id:
            item['client_id'] = server.client_id
        if server.client_secret:
            item['client_secret'] = server.client_secret
        if server.token_url:
            item['token_url'] = server.token_url
        self.mcp_table.put_item(Item=item)

    def list_mcp_servers(self, user_id: str) -> list[HttpMCPServer]:
        """
        List MCP servers for a specific user from Amazon DynamoDB.
        Includes both user-specific and public servers.
        
        :param user_id: The user ID for data isolation.
        :return: A list of HttpMCPServer objects.
        """
        # table = self.dynamodb.Table(self.dynamodb_table_name)
        keys = [user_id, 'public']
        items = []
        
        for k in keys:
            response = self.mcp_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(k),
                Limit=100
            )
            items.extend(response.get('Items', []))

        self.mcp_servers = [HttpMCPServer.model_validate(item) for item in items]
        return self.mcp_servers
        

    def get_mcp_server(self, user_id: str, id: str) -> HttpMCPServer | None:
        """
        Retrieve an MCP server by its ID from Amazon DynamoDB.
        Checks both user-specific and public data.

        :param user_id: The user ID for data isolation.
        :param id: The ID of the MCP server to retrieve.
        :return: An HttpMCPServer object if found, otherwise None.
        """
        # table = self.dynamodb.Table(self.dynamodb_table_name)
        keys = [user_id, 'public']
        
        for k in keys:
            response = self.mcp_table.get_item(Key={'user_id': k, 'id': id})
            if 'Item' in response:
                item = response['Item']
                return HttpMCPServer.model_validate(item)
        return None
        

    def delete_mcp_server(self, user_id: str, id: str) -> bool:
        """
        Delete an MCP server by its ID from Amazon DynamoDB.

        :param user_id: The user ID for data isolation.
        :param id: The ID of the MCP server to delete.
        :return: True if deletion was successful, False otherwise.
        """
        response = self.mcp_table.delete_item(
            Key={'user_id': user_id, 'id': id}
        )
        return response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200
