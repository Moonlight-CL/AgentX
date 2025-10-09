# Strands Agentic - AgentX

AgentX is an agent management platform built on top of the Strands framework, allowing you to create, manage, and orchestrate AI agents with various tools and capabilities. It follows the principle:

**Agent = LLM Model + System Prompt + Tools + Environment**

## 🌟 Features

- **Agent Management**: Create, configure, and manage AI agents through a user-friendly interface
- **Multiple Model Support**: Use models from Bedrock, OpenAI, Anthropic, LiteLLM, Ollama, or custom providers
- **Extensive Tool Library**: Equip agents with tools for RAG, file operations, web interactions, image generation, and more
- **Agent Orchestration**: Create orchestrator agents that can coordinate with other agents
- **Scheduling**: Schedule agent tasks to run automatically at specified times
- **MCP Integration**: Extend agent capabilities with Model Context Protocol servers

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
   
   For local development, you need to create the following DynamoDB tables:
   
   - **AgentTable**
     - Partition key: `id` (String)
   
   - **ChatRecordTable**
     - Partition key: `id` (String)
   
   - **ChatResponseTable**
     - Partition key: `id` (String)
     - Sort key: `resp_no` (Number)
   
   - **HttpMCPTable**
     - Partition key: `id` (String)
   
   - **AgentScheduleTable**
     - Partition key: `id` (String)

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
