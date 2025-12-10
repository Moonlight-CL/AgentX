# REST MCP Adapter

A generic adapter layer that allows agents to call MCP tools which transparently proxy to external REST APIs.

## Setup

### 1. Create DynamoDB Table

```bash
python scripts/create_rest_api_table.py
```

This creates the `RestAPIRegistry` table with:
- Primary Key: `user_id` (String)
- Sort Key: `api_id` (String)

### 2. Install Dependencies

The adapter requires `httpx` for HTTP requests:

```bash
uv add httpx
```

## API Endpoints

### Create REST API

```bash
POST /rest-apis
Headers: x-user-id: <user_id>
Body:
{
  "name": "Material Management API",
  "base_url": "https://api.example.com",
  "auth_type": "bearer",
  "auth_config": {
    "header": "Authorization",
    "value": "Bearer abc123..."
  },
  "endpoints": [
    {
      "path": "/api/material_list",
      "method": "GET",
      "tool_name": "get_material_list",
      "tool_description": "Retrieve list of materials",
      "parameters": {
        "query": {
          "page": "integer",
          "limit": "integer"
        }
      }
    }
  ]
}
```

### List REST APIs

```bash
GET /rest-apis
Headers: x-user-id: <user_id>
```

### Get REST API

```bash
GET /rest-apis/{api_id}
Headers: x-user-id: <user_id>
```

### Update REST API

```bash
PUT /rest-apis/{api_id}
Headers: x-user-id: <user_id>
Body: <same as create>
```

### Delete REST API

```bash
DELETE /rest-apis/{api_id}
Headers: x-user-id: <user_id>
```

### Test Endpoint

```bash
POST /rest-apis/{api_id}/test
Headers: x-user-id: <user_id>
Body:
{
  "endpoint_path": "/api/material_list",
  "params": {
    "page": 1,
    "limit": 10
  }
}
```

## How It Works

1. **Admin registers REST API** via the REST API endpoints
2. **Endpoints are stored** in DynamoDB with tool definitions
3. **When agent is created**, REST API tools are automatically loaded
4. **Agent can call tools** like any other MCP tool
5. **Adapter proxies** the call to the external REST API
6. **Response is returned** to the agent

## Authentication Types

- `bearer`: Bearer token authentication
- `api_key`: API key authentication
- `basic`: Basic authentication
- `none`: No authentication

## Example Usage

```python
# Register a REST API
import requests

response = requests.post(
    "http://localhost:8000/rest-apis",
    headers={"x-user-id": "user123"},
    json={
        "name": "Material API",
        "base_url": "https://api.example.com",
        "auth_type": "bearer",
        "auth_config": {
            "header": "Authorization",
            "value": "Bearer token123"
        },
        "endpoints": [
            {
                "path": "/materials",
                "method": "GET",
                "tool_name": "list_materials",
                "tool_description": "List all materials",
                "parameters": {
                    "query": {
                        "page": "integer",
                        "limit": "integer"
                    }
                }
            }
        ]
    }
)

# Now when you create an agent for user123, 
# it will automatically have the "list_materials" tool available
```

## Architecture

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
│        │        │     │ /api/materials   │
│        ▼        │     └──────────────────┘
│  ┌───────────┐  │
│  │ Registry  │  │
│  │ (DynamoDB)│  │
│  └───────────┘  │
└─────────────────┘
```

## Key Features

- **Zero Code Changes**: Add new REST APIs without modifying agent platform code
- **User Isolation**: Each user manages their own REST API integrations
- **Dynamic Tool Generation**: Tools created on-the-fly from registry
- **Reusability**: Same REST API can be used across multiple agents
- **Testability**: Validate endpoints before enabling for agents
