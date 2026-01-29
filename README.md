# AgentX - AI Agent Management Platform

AgentX is an enterprise-grade AI agent management platform built on the [Strands Agents](https://github.com/strands-agents/strands-agents) framework. It enables you to create, manage, and orchestrate AI agents with various tools and capabilities.

**Core Principle**: `Agent = LLM Model + System Prompt + Tools + Environment`

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AgentX Platform                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────┐    ┌──────────────────────────────────┐  │
│  │   Frontend (React)   │    │         Backend (FastAPI)         │  │
│  │                      │    │                                    │  │
│  │  • Agent Management  │    │  • RESTful APIs                   │  │
│  │  • Chat Interface    │◄──►│  • WebSocket Streaming            │  │
│  │  • Schedule Manager  │    │  • Agent Orchestration            │  │
│  │  • MCP Configuration │    │  • MCP Integration                │  │
│  │  • REST API Manager  │    │  • Schedule Service               │  │
│  │  • Orchestration     │    │  • User Authentication            │  │
│  └──────────────────────┘    └──────────────────────────────────┘  │
│                                           │                          │
│                                           ▼                          │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                      AWS Infrastructure                        │  │
│  │                                                                │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │  │
│  │  │  DynamoDB   │  │ EventBridge │  │  Lambda Functions   │   │  │
│  │  │  (11 Tables)│  │  Scheduler  │  │  (Schedule Executor)│   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘   │  │
│  │                                                                │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │  │
│  │  │  ECS/Fargate│  │     ALB     │  │  Bedrock AgentCore  │   │  │
│  │  │  (Containers)│ │(Load Balancer)│ │    Runtime         │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Features

### Agent Management
- **Create & Configure Agents**: Define agents with custom system prompts, tools, and model configurations
- **Multiple LLM Providers**: Support for Amazon Bedrock, OpenAI, Anthropic, LiteLLM, Ollama, and custom providers
- **Tool Library**: 50+ built-in tools for RAG, file operations, web interactions, image generation, code execution, and more
- **Agent Orchestration**: Create orchestrator agents that coordinate multiple agents for complex workflows

### Chat & Interaction
- **Real-time Streaming**: WebSocket-based streaming for instant responses
- **Chat History**: Persistent conversation history with session management
- **File Uploads**: Support for uploading files as context for agent conversations

### Scheduling & Automation
- **Scheduled Tasks**: Schedule agents to run automatically using cron expressions
- **AWS EventBridge Integration**: Enterprise-grade task scheduling with EventBridge Scheduler
- **Lambda Execution**: Serverless execution of scheduled agent tasks

### Integration & Extensibility
- **MCP Integration**: Connect Model Context Protocol (MCP) servers to extend agent capabilities
- **REST API Adapter**: Register external REST APIs as tools without code changes
- **OAuth Support**: Client Credentials Flow authentication for MCP servers

### Enterprise Features
- **User Authentication**: JWT-based authentication with optional Azure AD SSO
- **Multi-tenant Data Isolation**: Complete data isolation between users
- **Scalable Architecture**: AWS ECS with auto-scaling capabilities
- **High Availability**: Multi-AZ deployment with Application Load Balancer

## Project Structure

```
agentX/
├── be/                     # Backend (FastAPI + Strands)
│   ├── app/
│   │   ├── main.py         # Application entry point
│   │   ├── agent/          # Agent logic and event handling
│   │   ├── routers/        # API route definitions
│   │   ├── mcp/            # MCP integration
│   │   ├── schedule/       # Scheduling service
│   │   ├── orchestration/  # Agent orchestration
│   │   ├── user/           # User authentication
│   │   └── services/       # REST API adapter
│   ├── Dockerfile
│   └── pyproject.toml
├── fe/                     # Frontend (React + TypeScript)
│   ├── src/
│   │   ├── components/     # UI components
│   │   ├── store/          # Zustand state management
│   │   ├── services/       # API client
│   │   └── types/          # TypeScript definitions
│   ├── Dockerfile
│   └── package.json
├── cdk/                    # AWS CDK Infrastructure
│   ├── bin/                # CDK entry points
│   ├── lib/                # Stack definitions
│   │   ├── agentx-stack-combined.ts
│   │   ├── agent-schedule-stack.ts
│   │   └── lambda/         # Lambda functions
│   └── deploy.sh           # Deployment script
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.13+ with [uv](https://github.com/astral-sh/uv)
- Node.js 18+ with Bun (or npm)
- AWS account with configured credentials
- Docker (for containerized deployment)

### Local Development

**1. Start the Backend**

```bash
cd be
uv sync
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**2. Start the Frontend**

```bash
cd fe
bun install
bun run dev
```

**3. Access the Application**

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Environment Variables

**Backend (`be/.env`)**

```bash
# AWS Configuration
AWS_REGION=us-west-2

# Authentication
JWT_SECRET_KEY=your-secure-jwt-secret

# Azure AD SSO (Optional)
AZURE_CLIENT_ID=your-azure-client-id
AZURE_TENANT_ID=your-azure-tenant-id
AZURE_CLIENT_SECRET=your-azure-client-secret

# Scheduling (When deployed to AWS)
LAMBDA_FUNCTION_ARN=arn:aws:lambda:...
SCHEDULE_ROLE_ARN=arn:aws:iam:...
```

**Frontend (`fe/.env`)**

```bash
# API Configuration
VITE_API_BASE_URL=http://localhost:8000

# Azure AD SSO (Optional)
VITE_AZURE_CLIENT_ID=your-azure-client-id
VITE_AZURE_AUTHORITY=https://login.microsoftonline.com/your-tenant-id
```

### DynamoDB Tables

For local development, create the following DynamoDB tables:

| Table Name | Partition Key | Sort Key | Purpose |
|------------|---------------|----------|---------|
| UserTable | user_id (S) | - | User authentication |
| AgentTable | user_id (S) | id (S) | Agent configurations |
| ChatRecordTable | user_id (S) | id (S) | Chat sessions |
| ChatResponseTable | id (S) | resp_no (N) | Chat messages |
| ChatSessionTable | PK (S) | SK (S) | Session memory |
| HttpMCPTable | user_id (S) | id (S) | MCP server configs |
| RestAPIRegistryTable | user_id (S) | api_id (S) | REST API configs |
| AgentScheduleTable | user_id (S) | id (S) | Scheduled tasks |
| OrcheTable | user_id (S) | id (S) | Orchestration workflows |
| OrcheExecTable | user_id (S) | id (S) | Workflow executions |
| ConfTable | key (S) | - | System configurations |

> When deploying to AWS with CDK, these tables are created automatically.

## AWS Deployment

For production deployment to AWS, see the [Deployment Guide](README-DEPLOYMENT.md).

**Quick Deploy**

```bash
cd cdk

# Deploy with defaults (creates new VPC)
./deploy.sh --region us-west-2

# Deploy with existing VPC and Azure AD SSO
./deploy.sh --region us-west-2 \
  --vpc-id vpc-12345678 \
  --azure-client-id your-client-id \
  --azure-tenant-id your-tenant-id \
  --jwt-secret-key your-jwt-secret
```

## Documentation

| Document | Description |
|----------|-------------|
| [Deployment Guide](README-DEPLOYMENT.md) | Complete AWS deployment instructions |
| [Backend API](be/README.md) | Backend API documentation |
| [Frontend](fe/README.md) | Frontend development guide |
| [CDK Infrastructure](cdk/README.md) | AWS CDK deployment details |
| [REST API Adapter](be/REST_API_ADAPTER_README.md) | External REST API integration |

## Technology Stack

| Component | Technologies |
|-----------|--------------|
| **Backend** | FastAPI, Strands Agents, Boto3, PyJWT, WebSockets |
| **Frontend** | React 18, TypeScript, Vite, Ant Design, Zustand, XYFlow |
| **Infrastructure** | AWS CDK, ECS Fargate, DynamoDB, Lambda, EventBridge, ALB |
| **Authentication** | JWT, Azure AD (MSAL), PBKDF2 |

## License

This project is licensed under the MIT License - see the LICENSE file for details.
