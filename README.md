# Strands Agentic - AgentX

AgentX is an agent management platform built on top of the Strands framework, allowing you to create, manage, and orchestrate AI agents with various tools and capabilities. It follows the principle:

**Agent = LLM Model + System Prompt + Tools + Environment**

## Features

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
- **MCP Integration**: Support for adding custom HTTP MCP (Model Context Protocol) servers to extend agent functionality

### Enterprise Features
- **Scalable Architecture**: Built on AWS ECS with auto-scaling capabilities
- **High Availability**: Multi-AZ deployment with load balancing
- **Monitoring & Logging**: Comprehensive logging with CloudWatch integration
- **Security**: IAM-based access control and VPC isolation

## Architecture

The project consists of two main components:

### Backend (be/)

A FastAPI-based API server that provides:
- RESTful APIs for agent management
- WebSocket endpoints for streaming chat with agents
- Integration with AWS services (DynamoDB, EventBridge, Lambda)

### Frontend (fe/)

A React/TypeScript application built with:
- Vite for fast development and optimized builds
- Ant Design for UI components
- Zustand for state management
- TypeScript for type safety

## Getting Started

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

   **Advanced Features:**

   - **HttpMCPTable** (HTTP MCP server configurations)
     - Partition key: `user_id` (String)
     - Sort key: `id` (String)

   - **RestAPIRegistryTable** (REST API adapter configurations)
     - Partition key: `user_id` (String)
     - Sort key: `api_id` (String)
     - Purpose: Stores REST API configurations for integration with agents

   - **AgentScheduleTable** (Scheduled agent tasks)
     - Partition key: `user_id` (String)
     - Sort key: `id` (String)

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

## Deployment

The deployment process consists of three main steps:

1. **Create ECR repositories** for storing Docker images
2. **Build and push Docker images** to ECR
3. **Deploy the infrastructure** using AWS CDK

For detailed deployment instructions, see [README-DEPLOYMENT.md](README-DEPLOYMENT.md).

## Documentation

- [Backend API Documentation](be/README.md)
- [Frontend Documentation](fe/README.md)
- [CDK Deployment Documentation](cdk/README.md)

## Technologies

- **Backend**: FastAPI, Strands, Boto3, DynamoDB, EventBridge
- **Frontend**: React, TypeScript, Vite, Ant Design, Zustand
- **Deployment**: Docker, AWS CDK, ECS, ECR

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
