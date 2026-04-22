# Strands Agentic - AgentX

[![Awesome Strands Agents](https://img.shields.io/badge/Awesome-Strands%20Agents-00FF77?style=flat-square&logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjkwIiBoZWlnaHQ9IjQ2MyIgdmlld0JveD0iMCAwIDI5MCA0NjMiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik05Ny4yOTAyIDUyLjc4ODRDODUuMDY3NCA0OS4xNjY3IDcyLjIyMzQgNTYuMTM4OSA2OC42MDE3IDY4LjM2MTZDNjQuOTgwMSA4MC41ODQzIDcxLjk1MjQgOTMuNDI4MyA4NC4xNzQ5IDk3LjA1MDFMMjM1LjExNyAxMzkuNzc1QzI0NS4yMjMgMTQyLjc2OSAyNDYuMzU3IDE1Ni42MjggMjM2Ljg3NCAxNjEuMjI2TDMyLjU0NiAyNjAuMjkxQy0xNC45NDM5IDI4My4zMTYgLTkuMTYxMDcgMzUyLjc0IDQxLjQ4MzUgMzY3LjU5MUwxODkuNTUxIDQxMS4wMDlMMTkwLjEyNSA0MTEuMTY5QzIwMi4xODMgNDE0LjM3NiAyMTQuNjY1IDQwNy4zOTYgMjE4LjE5NiAzOTUuMzU1QzIyMS43ODQgMzgzLjEyMiAyMTQuNzc0IDM3MC4yOTYgMjAyLjU0MSAzNjYuNzA5TDU0LjQ3MzggMzIzLjI5MUM0NC4zNDQ3IDMyMC4zMjEgNDMuMTg3OSAzMDYuNDM2IDUyLjY4NTcgMzAxLjgzMUwyNTcuMDE0IDIwMi43NjZDMzA0LjQzMiAxNzkuNzc2IDI5OC43NTggMTEwLjQ4MyAyNDguMjMzIDk1LjUxMkw5Ny4yOTAyIDUyLjc4ODRaIiBmaWxsPSIjRkZGRkZGIi8+CjxwYXRoIGQ9Ik0yNTkuMTQ3IDAuOTgxODEyQzI3MS4zODkgLTIuNTc0OTggMjg0LjE5NyA0LjQ2NTcxIDI4Ny43NTQgMTYuNzA3NEMyOTEuMzExIDI4Ljk0OTIgMjg0LjI3IDQxLjc1NyAyNzIuMDI4IDQ1LjMxMzhMNzEuMTcyNyAxMDMuNjcxQzQwLjcxNDIgMTEyLjUyMSAzNy4xOTc2IDE1NC4yNjIgNjUuNzQ1OSAxNjguMDgzTDI0MS4zNDMgMjUzLjA5M0MzMDcuODcyIDI4NS4zMDIgMjk5Ljc5NCAzODIuNTQ2IDIyOC44NjIgNDAzLjMzNkwzMC40MDQxIDQ2MS41MDJDMTguMTcwNyA0NjUuMDg4IDUuMzQ3MDggNDU4LjA3OCAxLjc2MTUzIDQ0NS44NDRDLTEuODIzOSA0MzMuNjExIDUuMTg2MzcgNDIwLjc4NyAxNy40MTk3IDQxNy4yMDJMMjE1Ljg3OCAzNTkuMDM1QzI0Ni4yNzcgMzUwLjEyNSAyNDkuNzM5IDMwOC40NDkgMjIxLjIyNiAyOTQuNjQ1TDQ1LjYyOTcgMjA5LjYzNUMtMjAuOTgzNCAxNzcuMzg2IC0xMi43NzcyIDc5Ljk4OTMgNTguMjkyOCA1OS4zNDAyTDI1OS4xNDcgMC45ODE4MTJaIiBmaWxsPSIjRkZGRkZGIi8+Cjwvc3ZnPgo=&logoColor=white)](https://github.com/cagataycali/awesome-strands-agents)

AgentX is an agent management platform built on top of the Strands framework, allowing you to create, manage, and orchestrate AI agents with various tools and capabilities. It follows the principle:

**Agent = LLM Model + System Prompt + Tools + Environment**

## 🌟 Features

### Core Platform Features
- **User Authentication**: Secure user registration and login system with JWT token-based authentication
  - **Local Authentication**: Username/password-based registration and login
  - **Azure AD SSO**: Enterprise single sign-on integration with Microsoft Azure Active Directory
  - **Hybrid Authentication**: Support both local and Azure AD authentication methods simultaneously
- **Data Isolation**: Each user's agents, chat records, and data are completely isolated from other users
- **Agent Management**: Create, configure, and manage AI agents through a user-friendly interface
- **Multiple Model Support**: Use models from Bedrock, OpenAI, Anthropic, LiteLLM, Ollama, or custom providers
- **Chat History Management**: View, manage, and delete your conversation history with proper error handling

### Advanced Capabilities
- **Extensive Tool Library**: Equip agents with tools for RAG, file operations, web interactions, image generation, and more
- **Agent Orchestration**: Create orchestrator agents that can coordinate with other agents to handle complex workflows
- **Scheduling System**: Schedule agent tasks to run automatically at specified times using AWS EventBridge
- **Configuration Management**: Centralized configuration system for managing agent settings and preferences

### MCP Integration
- **Model Context Protocol Support**: Extend agent capabilities with specialized MCP servers
- **Database Integration**: Connect to MySQL, Redshift, DuckDB, and OpenSearch databases
- **AWS Services Integration**: Built-in AWS database evaluation and analysis tools
- **Custom MCP Servers**: Support for adding custom MCP servers to extend functionality

### Enterprise Features
- **Scalable Architecture**: Built on AWS ECS with auto-scaling capabilities
- **High Availability**: Multi-AZ deployment with load balancing
- **Monitoring & Logging**: Comprehensive logging with CloudWatch integration
- **Security**: IAM-based access control and VPC isolation

## 🏗️ Architecture

The project consists of three main components:

### 🔙 Backend (be/)

A FastAPI-based API server that provides:
- RESTful APIs for agent management
- WebSocket endpoints for streaming chat with agents
- Integration with AWS services (DynamoDB, EventBridge, Lambda)

### 🖥️ Frontend (fe/)

A React/TypeScript application built with:
- Vite for fast development and optimized builds
- Ant Design for UI components
- Zustand for state management
- TypeScript for type safety

### 🔌 MCP Servers (mcp/)

Model Context Protocol servers that extend agent capabilities:
- **MySQL MCP**: Tools for interacting with MySQL databases
- **Redshift MCP**: Tools for interacting with Amazon Redshift
- **DuckDB MCP**: Tools for interacting with DuckDB databases
- **OpenSearch MCP**: Tools for interacting with OpenSearch

## 🚀 Getting Started

### Prerequisites

- Python 3.13+
- Node.js 18+ and Bun
- Docker (for containerized deployment)
- AWS account (for AWS services)
- Azure AD tenant (optional, for Azure AD SSO)

### Azure AD SSO Configuration (Optional)

AgentX supports Azure AD single sign-on for enterprise authentication. To enable Azure AD SSO:

#### 1. Azure AD App Registration

1. Go to [Azure Portal](https://portal.azure.com) → Azure Active Directory → App registrations
2. Click "New registration"
3. Configure the application:
   - **Name**: AgentX (or your preferred name)
   - **Supported account types**: Choose based on your requirements
   - **Redirect URI**: 
     - Type: Single-page application (SPA)
     - URI: `http://localhost:5173` (for local development) or your production URL
4. After registration, note down:
   - **Application (client) ID**
   - **Directory (tenant) ID**

#### 2. Configure API Permissions

1. In your app registration, go to "API permissions"
2. Add the following Microsoft Graph permissions:
   - `User.Read` (Delegated)
   - `openid` (Delegated)
   - `profile` (Delegated)
   - `email` (Delegated)
3. Grant admin consent for your organization (if required)

#### 3. Backend Configuration

Create or update `be/.env` file:

```bash
# JWT Configuration (required for all authentication methods)
JWT_SECRET_KEY=your-jwt-secret-key-change-this-in-production

# Azure AD Configuration (optional, for SSO)
AZURE_CLIENT_ID=your-azure-client-id
AZURE_TENANT_ID=your-azure-tenant-id
AZURE_CLIENT_SECRET=your-azure-client-secret  # Optional, for server-side flows
AZURE_AUTHORITY=https://login.microsoftonline.com/your-azure-tenant-id

# AWS Configuration (for DynamoDB and other AWS services)
AWS_REGION=us-east-1
```

#### 4. Frontend Configuration

Create or update `fe/.env` file:

```bash
# Azure AD Configuration (optional, for SSO)
VITE_AZURE_CLIENT_ID=your-azure-client-id
VITE_AZURE_AUTHORITY=https://login.microsoftonline.com/your-azure-tenant-id
VITE_AZURE_REDIRECT_URI=http://localhost:5173  # Optional, defaults to current origin
VITE_AZURE_POST_LOGOUT_REDIRECT_URI=http://localhost:5173  # Optional
```

#### 5. How Azure AD SSO Works

1. **User Login Flow**:
   - User clicks "Sign in with Microsoft" button
   - Frontend redirects to Azure AD login page
   - User authenticates with Azure AD credentials
   - Azure AD returns access token and ID token
   - Frontend sends tokens to backend `/user/azure-login` endpoint
   - Backend verifies tokens and creates/updates user account
   - Backend returns local JWT token for subsequent API calls

2. **Token Verification**:
   - Backend verifies Azure AD tokens using Microsoft's public keys
   - Extracts user information (email, name, object ID)
   - Creates or updates user record in DynamoDB
   - Issues local JWT token for API authentication

3. **User Data Synchronization**:
   - User profile information is synchronized from Azure AD
   - Azure Object ID is stored for user identification
   - User groups and roles can be mapped from Azure AD

#### 6. Hybrid Authentication

AgentX supports both local and Azure AD authentication simultaneously:

- **Local users**: Register with username/password, authenticate with local credentials
- **Azure AD users**: Sign in with Microsoft, automatically provisioned on first login
- **Seamless integration**: Both authentication methods use the same JWT token system for API access

### Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/agentx.git
   cd agentx
   ```

2. **Set up the backend**:
   ```bash
   cd be
   uv sync
   source .venv/bin/python3
   uvicorn app.main:app --reload --loop asyncio
   ```

3. **Set up local DynamoDB tables**:
   
   For local development, you need to create the following DynamoDB tables. These tables support the core functionality of AgentX including user management, agent storage, chat history, and MCP server configuration:
   
   **Core Tables:**
   
   - **UserTable** (User authentication and management)
     - Partition key: `user_id` (String)
   
   - **AgentTable** (Agent configurations and metadata)
     - Partition key: `user_id` (String)
     - Sort key: `id` (String)
   
   - **ChatRecordTable** (Chat session records)
     - Partition key: `user_id` (String)
     - Sort key: `id` (String)
   
   - **ChatResponseTable** (Individual chat messages and responses)
     - Partition key: `id` (String)
     - Sort key: `resp_no` (Number)
   
   - **ChatSessionTable** (Chat session management and memory storage)
     - Partition key: `PK` (String)
     - Sort key: `SK` (String)
   
   **MCP and Advanced Features:**
   
   - **HttpMCPTable** (MCP server configurations)
     - Partition key: `user_id` (String)
     - Sort key: `id` (String)
   
   - **RestAPIRegistry** (REST API adapter configurations)
     - Partition key: `user_id` (String)
     - Sort key: `api_id` (String)
   
   - **AgentScheduleTable** (Scheduled agent tasks)
     - Partition key: `id` (String)
   
   **Additional Tables** (used by orchestration and configuration features):
   
   - **OrcheTable** (Orchestration workflows)
     - Partition key: `user_id` (String)
     - Sort key: `id` (String)
   
   - **ConfTable** (System configurations)
     - Partition key: `key` (String)
   
   > **Note**: When deploying to AWS, these tables are automatically created by the CDK stack. For local development with DynamoDB Local, you'll need to create them manually or use the AWS CLI with `--endpoint-url` pointing to your local DynamoDB instance.

4. **Set up the frontend**:
   ```bash
   cd fe
   bun install
   bun run dev
   ```

5. **Set up MCP servers** (optional):
   ```bash
   # For MySQL MCP
   cd mcp/mysql
   bun install
   bun run index.ts --transport http --port 3000
   
   # For Redshift MCP
   cd mcp/redshift
   uv sync
   python -m redshift_mcp_server --transport streamable-http --port 3001
   
   # For DuckDB MCP
   cd mcp/duckdb
   # Follow setup instructions in the directory
   
   # For OpenSearch MCP
   cd mcp/opensearch
   # Follow setup instructions in the directory
   ```

## 📦 Deployment

The deployment process consists of three main steps:

1. **Create ECR repositories** for storing Docker images
2. **Build and push Docker images** to ECR
3. **Deploy the infrastructure** using AWS CDK

For detailed deployment instructions, see [README-DEPLOYMENT.md](README-DEPLOYMENT.md).

## 📚 Documentation

- [Backend API Documentation](be/README.md)
- [Frontend Documentation](fe/README.md)
- [MySQL MCP Server Documentation](mcp/mysql/README.md)
- [Redshift MCP Server Documentation](mcp/redshift/README.md)
- [DuckDB MCP Server Documentation](mcp/duckdb/README.md)
- [OpenSearch MCP Server Documentation](mcp/opensearch/README.md)

## 🛠️ Technologies

- **Backend**: FastAPI, Strands, Boto3, DynamoDB, EventBridge
- **Frontend**: React, TypeScript, Vite, Ant Design, Zustand
- **MCP Servers**: Python, Bun, MySQL, Redshift
- **Deployment**: Docker, AWS CDK, ECS, ECR

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
