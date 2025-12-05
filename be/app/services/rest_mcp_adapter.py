from typing import Any, Dict, List
import httpx
from strands import tool


class RestMCPAdapter:
    def __init__(self, registry_service):
        self.registry = registry_service
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def generate_tools(self, user_id: str) -> List:
        """Generate MCP tools from user's REST API registry"""
        apis = await self.registry.get_user_apis(user_id)
        tools = []
        
        for api in apis:
            for endpoint in api.get('endpoints', []):
                tool_func = self._create_tool(api, endpoint)
                tools.append(tool_func)
        
        return tools
    
    def _create_tool(self, api: Dict, endpoint: Dict):
        """Create a single MCP tool from endpoint definition"""
        tool_name = endpoint['tool_name']
        tool_description = endpoint['tool_description']
        
        # Create the async function that will be decorated
        async def tool_func(**kwargs) -> str:
            return await self._execute_request(api, endpoint, kwargs)
        
        # Apply the @tool decorator
        return tool(name=tool_name, description=tool_description)(tool_func)
    
    async def _execute_request(self, api: Dict, endpoint: Dict, params: Dict) -> str:
        """Execute the actual REST API call"""
        url = f"{api['base_url']}{endpoint['path']}"
        method = endpoint['method'].lower()
        
        headers = self._build_headers(api['auth_type'], api['auth_config'])
        
        query_params = {k: v for k, v in params.items() 
                       if k in endpoint.get('parameters', {}).get('query', {})}
        body_params = {k: v for k, v in params.items() 
                      if k in endpoint.get('parameters', {}).get('body', {})}
        
        print(f"[REST API] Calling {method.upper()} {url}")
        print(f"[REST API] Headers: {headers}")
        print(f"[REST API] Query params: {query_params}")
        print(f"[REST API] Body params: {body_params}")
        
        try:
            response = await self.http_client.request(
                method=method,
                url=url,
                headers=headers,
                params=query_params if query_params else None,
                json=body_params if body_params else None
            )
            
            response.raise_for_status()
            print(f"[REST API] Response status: {response.status_code}")
            print(f"[REST API] Response body: {response.text[:500]}...")  # First 500 chars
            return response.text
        except Exception as e:
            print(f"[REST API] Error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"[REST API] Error response: {e.response.text}")
            raise
    
    def _build_headers(self, auth_type: str, auth_config: Dict) -> Dict:
        """Build authentication headers"""
        if auth_type == "none":
            return {}
        
        header_name = auth_config.get('header', 'Authorization')
        header_value = auth_config.get('value', '')
        
        return {header_name: header_value}
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()
