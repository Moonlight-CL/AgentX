# REST MCP Adapter Design

## Overview

A generic adapter layer that allows agents to call MCP tools which transparently proxy to external REST APIs. This enables integration with any REST API without modifying the agent platform code.

## Technical Design

### Core Components

#### 1. REST API Registry (DynamoDB Table)

```
RestAPIRegistryTable:
  PK: user_id (String)
  SK: api_id (String)
  
  Attributes:
  - name: "Material Management API"
  - base_url: "https://api.example.com"
  - auth_type: "bearer" | "api_key" | "basic" | "none"
  - auth_config: {header: "Authorization", value: "Bearer {token}"}
  - endpoints: [
      {
        path: "/api/material_list",
        method: "GET",
        tool_name: "get_material_list",
        tool_description: "Retrieve list of materials",
        parameters: {
          query: {page: "integer", limit: "integer"},
          headers: {optional_header: "string"}
        },
        response_mapping: null  // optional transformation
      }
    ]
```

#### 2. MCP Tool Generator

Dynamically generates MCP tools from REST API definitions:

```python
# be/app/services/rest_mcp_adapter.py
from typing import Any, Dict, List
import httpx
from strands.tool import Tool

class RestMCPAdapter:
    def __init__(self, registry_service):
        self.registry = registry_service
        self.http_client = httpx.AsyncClient()
    
    async def generate_tools(self, user_id: str) -> List[Tool]:
        """Generate MCP tools from user's REST API registry"""
        apis = await self.registry.get_user_apis(user_id)
        tools = []
        
        for api in apis:
            for endpoint in api['endpoints']:
                tool = self._create_tool(api, endpoint)
                tools.append(tool)
        
        return tools
    
    def _create_tool(self, api: Dict, endpoint: Dict) -> Tool:
        """Create a single MCP tool from endpoint definition"""
        async def tool_func(**kwargs) -> str:
            return await self._execute_request(api, endpoint, kwargs)
        
        # Build parameter schema
        params = {}
        if endpoint.get('parameters', {}).get('query'):
            params.update(endpoint['parameters']['query'])
        if endpoint.get('parameters', {}).get('body'):
            params.update(endpoint['parameters']['body'])
        
        return Tool(
            name=endpoint['tool_name'],
            description=endpoint['tool_description'],
            parameters=params,
            func=tool_func
        )
    
    async def _execute_request(self, api: Dict, endpoint: Dict, params: Dict) -> str:
        """Execute the actual REST API call"""
        url = f"{api['base_url']}{endpoint['path']}"
        method = endpoint['method'].lower()
        
        # Build headers
        headers = self._build_headers(api['auth_type'], api['auth_config'])
        
        # Separate query params and body
        query_params = {k: v for k, v in params.items() 
                       if k in endpoint.get('parameters', {}).get('query', {})}
        body_params = {k: v for k, v in params.items() 
                      if k in endpoint.get('parameters', {}).get('body', {})}
        
        # Execute request
        response = await self.http_client.request(
            method=method,
            url=url,
            headers=headers,
            params=query_params if query_params else None,
            json=body_params if body_params else None
        )
        
        response.raise_for_status()
        return response.text
    
    def _build_headers(self, auth_type: str, auth_config: Dict) -> Dict:
        """Build authentication headers"""
        if auth_type == "none":
            return {}
        
        header_name = auth_config.get('header', 'Authorization')
        header_value = auth_config.get('value', '')
        
        return {header_name: header_value}
```

#### 3. Integration with Agent Creation

```python
# be/app/api/agents.py
from app.services.rest_mcp_adapter import RestMCPAdapter

@router.post("/agents")
async def create_agent(agent_data: AgentCreate, user_id: str):
    # ... existing agent creation logic ...
    
    # Add REST API tools
    rest_adapter = RestMCPAdapter(registry_service)
    rest_tools = await rest_adapter.generate_tools(user_id)
    
    # Merge with other tools
    all_tools = agent_data.tools + rest_tools
    
    # Create agent with all tools
    agent = Agent(
        model=agent_data.model,
        system_prompt=agent_data.system_prompt,
        tools=all_tools
    )
```

## Admin Interaction Flow

### 1. REST API Management UI

Add new section in frontend for REST API management:

```typescript
// fe/src/pages/RestAPIManagement.tsx
interface RestAPIConfig {
  name: string;
  base_url: string;
  auth_type: 'bearer' | 'api_key' | 'basic' | 'none';
  auth_config: {
    header?: string;
    value?: string;
  };
  endpoints: EndpointConfig[];
}

interface EndpointConfig {
  path: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  tool_name: string;
  tool_description: string;
  parameters: {
    query?: Record<string, string>;
    body?: Record<string, string>;
    headers?: Record<string, string>;
  };
}
```

### 2. Admin Setup Steps

1. **Register REST API**
   - Name: "Material Management API"
   - Base URL: "https://api.example.com"
   - Auth Type: Bearer Token
   - Auth Header: "Authorization"
   - Auth Value: "Bearer abc123..."

2. **Define Endpoints**
   - Path: `/api/material_list`
   - Method: GET
   - Tool Name: `get_material_list`
   - Description: "Retrieve paginated list of materials"
   - Query Parameters:
     - `page`: integer (optional)
     - `limit`: integer (optional)

3. **Test Endpoint** (optional validation step)
   - Send test request with sample parameters
   - Verify response

4. **Enable for Agents**
   - REST API tools automatically available when creating/editing agents
   - Show in tool selection dropdown alongside other tools

## Backend API Endpoints

```python
# be/app/api/rest_apis.py
@router.post("/rest-apis")
async def create_rest_api(config: RestAPIConfig, user_id: str):
    """Register a new REST API"""
    pass

@router.get("/rest-apis")
async def list_rest_apis(user_id: str):
    """List user's registered REST APIs"""
    pass

@router.put("/rest-apis/{api_id}")
async def update_rest_api(api_id: str, config: RestAPIConfig, user_id: str):
    """Update REST API configuration"""
    pass

@router.delete("/rest-apis/{api_id}")
async def delete_rest_api(api_id: str, user_id: str):
    """Delete REST API"""
    pass

@router.post("/rest-apis/{api_id}/test")
async def test_endpoint(api_id: str, endpoint_path: str, params: Dict, user_id: str):
    """Test an endpoint before saving"""
    pass
```

## Key Benefits

1. **Zero Code Changes**: Add new REST APIs without modifying agent platform code
2. **User Isolation**: Each user manages their own REST API integrations
3. **Dynamic Tool Generation**: Tools created on-the-fly from registry
4. **Reusability**: Same REST API can be used across multiple agents
5. **Testability**: Validate endpoints before enabling for agents

## Example Usage Flow

```
Admin registers Material API 
  → Agent automatically gets `get_material_list` tool 
  → Agent can call it like any MCP tool 
  → Platform proxies to REST API 
  → Returns response to agent
```

## Architecture Diagram

```
┌─────────────────┐
│  Agent Platform │
│                 │
│  ┌───────────┐  │
│  │   Agent   │  │
│  └─────┬─────┘  │
│        │        │
│        ▼        │
│  ┌───────────┐  │     ┌──────────────────┐
│  │ REST MCP  │──┼────▶│  External REST   │
│  │  Adapter  │  │     │      APIs        │
│  └─────┬─────┘  │     │                  │
│        │        │     │ /api/material_   │
│        ▼        │     │      list        │
│  ┌───────────┐  │     └──────────────────┘
│  │ Registry  │  │
│  │ (DynamoDB)│  │
│  └───────────┘  │
└─────────────────┘
```

## Implementation Notes

- The adapter layer separates concerns: agent platform handles MCP orchestration, external systems expose REST APIs, and the adapter bridges them transparently
- Authentication credentials are stored securely in the registry per user
- Response transformations can be added via `response_mapping` for complex API responses
- Error handling should include retry logic and proper error messages back to the agent
