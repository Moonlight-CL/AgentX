# AgentX Backend

FastAPI-based backend server for the AgentX AI agent management platform, built on the [Strands Agents](https://github.com/strands-agents/strands-agents) framework.

## Features

- **Agent Management**: Create, configure, and manage AI agents with custom tools
- **Real-time Chat**: WebSocket streaming for interactive agent conversations
- **Schedule Management**: Create scheduled tasks using AWS EventBridge
- **MCP Integration**: Connect Model Context Protocol servers to extend agent capabilities
- **REST API Adapter**: Register external REST APIs as agent tools dynamically
- **Agent Orchestration**: Coordinate multiple agents for complex workflows
- **User Authentication**: JWT-based auth with optional Azure AD SSO

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- AWS credentials configured
- DynamoDB tables created (see main README)

### Installation

```bash
cd be
uv sync
```

### Running the Server

**Development**
```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Production**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Environment Variables

Create a `.env` file in the `be/` directory:

```bash
# AWS Configuration
AWS_REGION=us-west-2
# AWS_ACCESS_KEY_ID=your_key        # Optional if using IAM roles
# AWS_SECRET_ACCESS_KEY=your_secret # Optional if using IAM roles

# Authentication
JWT_SECRET_KEY=your-secure-jwt-secret-key

# Azure AD SSO (Optional)
AZURE_CLIENT_ID=your-azure-client-id
AZURE_TENANT_ID=your-azure-tenant-id
AZURE_CLIENT_SECRET=your-azure-client-secret

# File Storage
S3_BUCKET_NAME=agentx-files-bucket
S3_FILE_PREFIX=agentx/files

# Scheduling (When deployed to AWS)
LAMBDA_FUNCTION_ARN=arn:aws:lambda:region:account:function:name
SCHEDULE_ROLE_ARN=arn:aws:iam::account:role/role-name

# Service Authentication
SERVICE_API_KEY=your-service-api-key
```

## API Documentation

### API Endpoints

#### User Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/user/register` | Register new user |
| POST | `/api/user/login` | Login with username/password |
| POST | `/api/user/azure-login` | Login with Azure AD token |
| GET | `/api/user/profile` | Get current user profile |

#### Agent Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/agent/list` | List all user's agents |
| GET | `/api/agent/get/{agent_id}` | Get agent details |
| POST | `/api/agent/create` | Create new agent |
| PUT | `/api/agent/update/{agent_id}` | Update agent configuration |
| DELETE | `/api/agent/delete/{agent_id}` | Delete agent |
| POST | `/api/agent/stream_chat` | Stream chat with agent (WebSocket) |
| POST | `/api/agent/async_chat` | Async chat (for scheduled tasks) |

#### Chat Records

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chat/list` | List chat sessions |
| GET | `/api/chat/get/{chat_id}` | Get chat messages |
| DELETE | `/api/chat/delete/{chat_id}` | Delete chat session |

#### Schedule Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/schedule/list` | List all schedules |
| POST | `/api/schedule/create` | Create new schedule |
| PUT | `/api/schedule/update/{id}` | Update schedule |
| DELETE | `/api/schedule/delete/{id}` | Delete schedule |
| POST | `/api/schedule/toggle/{id}` | Enable/disable schedule |

#### MCP Server Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/mcp/list` | List MCP servers |
| POST | `/api/mcp/add` | Add MCP server |
| PUT | `/api/mcp/update/{id}` | Update MCP server |
| DELETE | `/api/mcp/delete/{id}` | Delete MCP server |
| GET | `/api/mcp/tools/{id}` | Get available tools |

#### REST API Adapter

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/rest-apis` | List REST APIs |
| POST | `/api/rest-apis` | Register REST API |
| GET | `/api/rest-apis/{id}` | Get REST API details |
| PUT | `/api/rest-apis/{id}` | Update REST API |
| DELETE | `/api/rest-apis/{id}` | Delete REST API |
| POST | `/api/rest-apis/{id}/test` | Test endpoint |

#### Orchestration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orchestration/list` | List workflows |
| POST | `/api/orchestration/create` | Create workflow |
| PUT | `/api/orchestration/update/{id}` | Update workflow |
| DELETE | `/api/orchestration/delete/{id}` | Delete workflow |
| POST | `/api/orchestration/execute/{id}` | Execute workflow |
| GET | `/api/orchestration/executions` | List executions |

#### File Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/files/upload` | Upload file to S3 |
| GET | `/api/files/download/{key}` | Download file |
| DELETE | `/api/files/delete/{key}` | Delete file |

## Agent Configuration

### Agent Types

**Standard Agent**
- Uses Strands Agents framework
- Configurable system prompt
- Selectable tools from the tool library
- Multiple LLM provider support

**Orchestrator Agent**
- Coordinates multiple agents
- Can use other agents as tools
- Supports complex multi-step workflows

### Built-in Tools

The platform provides 50+ built-in tools categorized as:

- **RAG & Memory**: Vector search, document retrieval, conversation memory
- **File Operations**: Read, write, list files
- **Web & Network**: HTTP requests, web scraping
- **Image Generation**: AI image creation
- **Code Execution**: Python, shell command execution
- **AWS Services**: S3, DynamoDB, Lambda interactions
- **Browser Automation**: AgentCore browser tools
- **Utilities**: Calculator, date/time, JSON processing

## Authentication

### JWT Authentication

All API endpoints (except `/user/register` and `/user/login`) require JWT authentication:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:8000/api/agent/list
```

### Service API Key

Lambda functions use API key authentication:

```bash
curl -H "X-API-Key: YOUR_SERVICE_API_KEY" http://localhost:8000/api/agent/async_chat
```

### Azure AD SSO

When configured, users can authenticate via Azure AD:

1. Frontend redirects to Azure AD login
2. User authenticates with Microsoft credentials
3. Frontend sends tokens to `/api/user/azure-login`
4. Backend validates tokens and issues JWT

## Deployment

For full AWS deployment, see the [Deployment Guide](../README-DEPLOYMENT.md).

## Dependencies

Key dependencies from `pyproject.toml`:

- **fastapi**: Web framework
- **strands-agents**: AI agent framework
- **strands-agents-tools**: Tool library
- **boto3**: AWS SDK
- **pyjwt**: JWT token handling
- **websockets**: WebSocket support
- **uvicorn**: ASGI server
