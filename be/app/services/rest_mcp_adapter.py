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
        
        # Build parameter schema from endpoint definition
        endpoint_params = endpoint.get('parameters', {}) or {}
        query_params = endpoint_params.get('query', {}) or {}
        body_params = endpoint_params.get('body', {}) or {}
        
        # Combine all parameters
        all_params = {**query_params, **body_params}
        
        # Create the async function that will be decorated
        async def tool_func(**kwargs) -> str:
            print(f"[REST API Tool] {tool_name} called with params: {kwargs}")
            return await self._execute_request(api, endpoint, kwargs)
        
        # Set parameter annotations for the tool decorator
        if all_params:
            annotations = {k: str for k in all_params.keys()}
            annotations['return'] = str
            tool_func.__annotations__ = annotations
        
        # Apply the @tool decorator
        return tool(name=tool_name, description=tool_description)(tool_func)
    
    async def _execute_request(self, api: Dict, endpoint: Dict, params: Dict) -> str:
        """Execute the actual REST API call"""
        try:
            print("[REST MCP Adapter] _execute_request entered")
            
            # Safe logging - convert to string explicitly to avoid repr() issues
            print(f"[REST API] Input api keys: {list(api.keys())}")
            print(f"[REST API] API name: {api.get('name')}, base_url: {api.get('base_url')}")
            print(f"[REST API] Auth type: {api.get('auth_type')}")
            print(f"[REST API] Endpoint: {endpoint.get('tool_name')} - {endpoint.get('method')} {endpoint.get('path')}")
            print(f"[REST API] Input params: {str(params)}")
            
            # Handle case where agent passes string in 'kwargs'
            if 'kwargs' in params and isinstance(params['kwargs'], str):
                kwargs_str = params['kwargs']
                print(f"[REST API] Parsing kwargs string: {kwargs_str[:100]}")
                
                # Try JSON first
                try:
                    import json
                    params = json.loads(kwargs_str)
                    print(f"[REST API] Parsed as JSON: {str(params)}")
                except json.JSONDecodeError:
                    # Try URL-encoded
                    from urllib.parse import parse_qs
                    parsed = parse_qs(kwargs_str)
                    params = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
                    print(f"[REST API] Parsed as URL-encoded: {str(params)}")
            
            url = f"{api['base_url']}{endpoint['path']}"
            method = endpoint['method'].lower()
            
            headers = self._build_headers(api['auth_type'], api.get('auth_config', {}))
            
            # Safely get parameters with defaults
            endpoint_params = endpoint.get('parameters', {}) or {}
            query_param_keys = endpoint_params.get('query', {}) or {}
            body_param_keys = endpoint_params.get('body', {}) or {}
            
            print(f"[REST API] Endpoint body param keys: {list(body_param_keys.keys())}")
            
            # Smart parameter routing: POST/PUT/PATCH → body, GET/DELETE → query
            if method in ['post', 'put', 'patch'] and body_param_keys:
                # For POST/PUT/PATCH, prefer body params
                body_params = {k: v for k, v in params.items() if k in body_param_keys}
                query_params = {k: v for k, v in params.items() if k in query_param_keys}
            else:
                # For GET/DELETE, prefer query params
                query_params = {k: v for k, v in params.items() if k in query_param_keys or not body_param_keys}
                body_params = {}
            
            print(f"[REST API] Calling {method.upper()} {url}")
            print(f"[REST API] Query params: {str(query_params)}")
            print(f"[REST API] Body params: {str(body_params)}")
            
            # Full request details before sending
            print("[REST API] === FULL REQUEST ===")
            print(f"[REST API] Method: {method.upper()}")
            print(f"[REST API] URL: {url}")
            print(f"[REST API] Headers: {headers}")
            print(f"[REST API] Query params: {query_params}")
            print(f"[REST API] Body (JSON): {body_params}")
            print("[REST API] === END REQUEST ===")
            
            print("[REST API] Making HTTP request...")
            response = await self.http_client.request(
                method=method,
                url=url,
                headers=headers,
                params=query_params if query_params else None,
                json=body_params if body_params else None
            )
            
            print(f"[REST API] Got response, status: {response.status_code}")
            print("[REST API] Checking status...")
            
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as status_err:
                # Handle HTTP errors with Unicode-safe logging
                error_body = status_err.response.text[:500].encode('utf-8', errors='replace').decode('utf-8')
                print(f"[REST API] HTTP Error {status_err.response.status_code}: {error_body}")
                raise
            
            print("[REST API] Status check passed")
            
            # Safe logging of response - handle Unicode
            response_length = len(response.text)
            print(f"[REST API] Response length: {response_length} chars")
            
            try:
                preview = response.text[:500].encode('utf-8', errors='replace').decode('utf-8')
                print(f"[REST API] Response preview: {preview}")
            except Exception as log_err:
                print(f"[REST API] Could not preview response: {type(log_err).__name__}")
            
            return response.text
        except Exception as e:
            print(f"[REST API] Error type: {type(e).__name__}")
            error_msg = str(e)[:200].encode('utf-8', errors='replace').decode('utf-8')
            print(f"[REST API] Error message: {error_msg}")
            
            if hasattr(e, 'response') and e.response is not None:
                error_resp = str(e.response.text[:200]).encode('utf-8', errors='replace').decode('utf-8')
                print(f"[REST API] Error response: {error_resp}")
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
