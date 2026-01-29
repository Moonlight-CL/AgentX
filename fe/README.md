# AgentX Frontend

React-based frontend application for the AgentX AI agent management platform, built with TypeScript, Vite, and Ant Design.

## Features

- **Agent Management**: Create, configure, and manage AI agents
- **Interactive Chat**: Real-time streaming chat with agents
- **Schedule Management**: Create and manage scheduled agent tasks
- **MCP Integration**: Configure Model Context Protocol servers
- **REST API Manager**: Register and manage external REST APIs
- **Orchestration Editor**: Visual workflow editor for agent orchestration
- **User Authentication**: Local login and Azure AD SSO support

## Quick Start

### Prerequisites

- Node.js 18+ or Bun
- Backend server running at http://localhost:8000

### Installation

```bash
cd fe

# Using Bun (recommended)
bun install

# Or using npm
npm install
```

### Running the Application

**Development**
```bash
# Using Bun
bun run dev

# Using npm
npm run dev
```

**Production Build**
```bash
# Using Bun
bun run build

# Using npm
npm run build

# Preview production build
bun run preview
```

### Environment Variables

Create a `.env` file in the `fe/` directory:

```bash
# API Configuration
VITE_API_BASE_URL=http://localhost:8000

# Azure AD SSO (Optional)
VITE_AZURE_CLIENT_ID=your-azure-client-id
VITE_AZURE_AUTHORITY=https://login.microsoftonline.com/your-tenant-id
VITE_AZURE_REDIRECT_URI=http://localhost:5173
VITE_AZURE_POST_LOGOUT_REDIRECT_URI=http://localhost:5173
```

## Application Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/login` | Login | User login page |
| `/register` | Register | User registration page |
| `/` | Chat | Main chat interface (default) |
| `/chat` | Chat | Chat with agents |
| `/agent` | Agent | Agent management |
| `/schedule` | Schedule | Scheduled tasks |
| `/mcp` | MCP | MCP server configuration |
| `/restapi` | RestAPI | REST API adapter management |
| `/orchestration` | OrchestrationManager | Workflow orchestration |
| `/config` | Config | System configuration |
| `/usecase` | UseCase | Use case templates |

## Azure AD SSO Integration

When Azure AD is configured:

1. "Sign in with Microsoft" button appears on login page
2. Uses MSAL React library for authentication
3. Tokens are validated by backend
4. User is automatically provisioned on first login

**Configuration Steps:**

1. Register app in Azure Portal
2. Add redirect URI: `http://localhost:5173` (or production URL)
3. Configure required permissions: `User.Read`, `openid`, `profile`, `email`
4. Set environment variables in `.env`

## Deployment

### Docker Build

```bash
docker build -t agentx-fe .
```

### Nginx Configuration

The Docker image uses Nginx to serve the built application with:
- SPA fallback routing
- Gzip compression
- Static asset caching

For full AWS deployment, see the [Deployment Guide](../README-DEPLOYMENT.md).

## Dependencies

Key dependencies from `package.json`:

| Package | Purpose |
|---------|---------|
| **react** | UI library |
| **typescript** | Type safety |
| **vite** | Build tool and dev server |
| **antd** | UI component library |
| **@ant-design/icons** | Icon library |
| **@ant-design/x** | Extended Ant Design components |
| **zustand** | State management |
| **axios** | HTTP client |
| **react-router-dom** | Routing |
| **@azure/msal-react** | Azure AD SSO |
| **@xyflow/react** | Flow diagram editor |
| **react-markdown** | Markdown rendering |
| **rehype-highlight** | Code syntax highlighting |
| **dayjs** | Date manipulation |
| **cron-validator** | Cron expression validation |
