import axios from 'axios';

// Base URL for API calls using Vite proxy
const BASE_URL = '/api';

// Agent API endpoints
const AGENT_API = {
  list: `${BASE_URL}/agent/list`,
  createOrUpdate: `${BASE_URL}/agent/createOrUpdate`,
  toolList: `${BASE_URL}/agent/tool_list`,
  delete: (id: string) => `${BASE_URL}/agent/delete/${id}`,
  streamChat: `${BASE_URL}/agent/stream_chat`,
};

// Chat API endpoints
const CHAT_API = {
  listRecords: `${BASE_URL}/chat/list_record`,
  listResponses: (chatId: string) => `${BASE_URL}/chat/list_chat_responses?chat_id=${chatId}`,
  deleteChat: (chatId: string) => `${BASE_URL}/chat/del_chat?chat_id=${chatId}`,
};

// MCP API endpoints
const MCP_API = {
  list: `${BASE_URL}/mcp/list`,
  createOrUpdate: `${BASE_URL}/mcp/createOrUpdate`,
  get: (id: string) => `${BASE_URL}/mcp/get/${id}`,
  delete: (id: string) => `${BASE_URL}/mcp/delete/${id}`,
};

// Schedule API endpoints
const SCHEDULE_API = {
  list: `${BASE_URL}/schedule/list`,
  create: `${BASE_URL}/schedule/create`,
  update: (id: string) => `${BASE_URL}/schedule/update/${id}`,
  delete: (id: string) => `${BASE_URL}/schedule/delete/${id}`,
};

// Agent types
export const AGENT_TYPES = {
  PLAIN: 1,
  ORCHESTRATOR: 2,
};

// Model providers
export const MODEL_PROVIDERS = {
  BEDROCK: 1,
  OPENAI: 2,
  ANTHROPIC: 3,
  LITELLM: 4,
  OLLAMA: 5,
  CUSTOM: 6,
};

// Tool types
export const TOOL_TYPES = {
  STRANDS: 1,
  MCP: 2,
  AGENT: 3,
  PYTHON: 4,
};

// Bedrock models
export const BEDROCK_MODELS = [
  'us.anthropic.claude-sonnet-4-20250514-v1:0',
  'us.anthropic.claude-3-7-sonnet-20250219-v1:0',
  'us.anthropic.claude-opus-4-20250514-v1:0',
  'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
  'qwen.qwen3-coder-480b-a35b-v1:0',
  'qwen.qwen3-235b-a22b-2507-v1:0'
];

export const OPENAI_MODELS = [
  'gpt-4',
  'gpt-4-turbo',
  'gpt-4o',
  'gpt-3.5-turbo',
  'GPT-5',
  'kimi-k2-250711'
]

// Interface for Tool
export interface Tool {
  name: string;
  display_name?: string; // Optional display name for better UI representation
  category: string;
  desc: string;
  type: number;
  mcp_server_url?: string;
  agent_id?: string;
}

// Interface for Agent
export interface Agent {
  id: string;
  name: string;
  display_name: string;
  description: string;
  agent_type: number;
  model_provider: number;
  model_id: string;
  sys_prompt: string;
  tools: Tool[];
  envs?: string;
  extras?: {
    base_url?: string;
    api_key?: string;
    [key: string]: any;
  };
  created_at?: string;
  updated_at?: string;
}

// Interface for MCP Server
export interface MCPServer {
  id: string;
  name: string;
  desc: string;
  host: string;
}

// Interface for ChatRecord
export interface ChatRecord {
  id: string;
  agent_id: string;
  user_message: string;
  create_time: string;
}

// Interface for ChatResponse
export interface ChatResponse {
  chat_id: string;
  resp_no: number;
  content: string;
  create_time: string;
}

// Interface for Schedule
export interface Schedule {
  id: string;
  agentId: string;
  agentName: string;
  cronExpression: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  user_message?: string;
}

// Mock data for schedules
const mockSchedules: Schedule[] = [
  {
    id: '1',
    agentId: '1',
    agentName: 'Calculator',
    cronExpression: '0 8 * * 1',
    status: 'ENABLED',
    createdAt: '2025-06-01T10:00:00Z',
    updatedAt: '2025-06-01T10:00:00Z',
  },
  {
    id: '2',
    agentId: '2',
    agentName: 'File Writer',
    cronExpression: '0 12 * * *',
    status: 'ENABLED',
    createdAt: '2025-06-02T14:30:00Z',
    updatedAt: '2025-06-02T14:30:00Z',
  },
];

// Mock data for agents
const mockAgents: Agent[] = [
  {
    id: '1',
    name: 'calculator',
    display_name: 'Calculator',
    description: 'A simple calculator agent that can perform basic arithmetic operations',
    agent_type: AGENT_TYPES.PLAIN,
    model_provider: MODEL_PROVIDERS.BEDROCK,
    model_id: 'us.anthropic.claude-3-7-sonnet-20250219-v1:0',
    sys_prompt: 'You are a calculator assistant. Help users perform calculations.',
    tools: [
      {
        name: 'basic_math',
        category: 'math',
        desc: 'Perform basic math operations',
        type: TOOL_TYPES.STRANDS,
      },
      {
        name: 'advanced_math',
        category: 'math',
        desc: 'Perform advanced math operations',
        type: TOOL_TYPES.STRANDS,
      },
      {
        name: 'unit_conversion',
        category: 'utility',
        desc: 'Convert between different units',
        type: TOOL_TYPES.STRANDS,
      },
    ],
    created_at: '2025-06-01T10:00:00Z',
    updated_at: '2025-06-01T10:00:00Z',
  },
  {
    id: '2',
    name: 'file_writer',
    display_name: 'File Writer',
    description: 'An agent that can create and modify files',
    agent_type: AGENT_TYPES.ORCHESTRATOR,
    model_provider: MODEL_PROVIDERS.OPENAI,
    model_id: 'gpt-4',
    sys_prompt: 'You are a file management assistant. Help users create and modify files.',
    tools: [
      {
        name: 'file_create',
        category: 'file',
        desc: 'Create a new file',
        type: TOOL_TYPES.STRANDS,
      },
      {
        name: 'file_read',
        category: 'file',
        desc: 'Read file contents',
        type: TOOL_TYPES.STRANDS,
      },
      {
        name: 'file_write',
        category: 'file',
        desc: 'Write to a file',
        type: TOOL_TYPES.STRANDS,
      },
    ],
    created_at: '2025-06-02T14:30:00Z',
    updated_at: '2025-06-02T14:30:00Z',
  },
];

// Mock data for MCP servers
const mockMCPServers: MCPServer[] = [
  {
    id: '1',
    name: 'MCP Server 1',
    desc: 'Primary MCP server for data processing',
    host: 'http://localhost:8001',
  },
  {
    id: '2',
    name: 'MCP Server 2',
    desc: 'Backup MCP server',
    host: 'http://localhost:8002',
  },
  {
    id: '3',
    name: 'MCP Server 3',
    desc: 'Specialized MCP server for image processing',
    host: 'http://localhost:8003',
  },
];

// Mock data for tools
const mockTools: Tool[] = [
  {
    name: 'basic_math',
    category: 'math',
    desc: 'Perform basic math operations',
    type: TOOL_TYPES.STRANDS,
  },
  {
    name: 'advanced_math',
    category: 'math',
    desc: 'Perform advanced math operations',
    type: TOOL_TYPES.STRANDS,
  },
  {
    name: 'unit_conversion',
    category: 'utility',
    desc: 'Convert between different units',
    type: TOOL_TYPES.STRANDS,
  },
  {
    name: 'file_create',
    category: 'file',
    desc: 'Create a new file',
    type: TOOL_TYPES.STRANDS,
  },
  {
    name: 'file_read',
    category: 'file',
    desc: 'Read file contents',
    type: TOOL_TYPES.STRANDS,
  },
  {
    name: 'file_write',
    category: 'file',
    desc: 'Write to a file',
    type: TOOL_TYPES.STRANDS,
  },
  {
    name: 'weather_api',
    category: 'api',
    desc: 'Get weather information',
    type: TOOL_TYPES.MCP,
    mcp_server_url: 'http://weather-api.example.com',
  },
  {
    name: 'translator',
    category: 'language',
    desc: 'Translate text between languages',
    type: TOOL_TYPES.AGENT,
    agent_id: '3',
  },
  {
    name: 'data_analysis',
    category: 'data',
    desc: 'Analyze data using Python',
    type: TOOL_TYPES.PYTHON,
  },
];

// API functions
export const mcpAPI = {
  // Get list of MCP servers
  getMCPServers: async (): Promise<MCPServer[]> => {
    try {
      const response = await axios.get(MCP_API.list);
      return response.data;
    } catch (error) {
      console.error('Error fetching MCP servers:', error);
      // Fallback to mock data if API call fails
      console.warn('Falling back to mock data');
      return mockMCPServers;
    }
  },
  
  // Get a specific MCP server
  getMCPServer: async (id: string): Promise<MCPServer | null> => {
    try {
      const response = await axios.get(MCP_API.get(id));
      return response.data;
    } catch (error) {
      console.error(`Error fetching MCP server with ID ${id}:`, error);
      // Fallback to mock data if API call fails
      console.warn('Falling back to mock data');
      return mockMCPServers.find(server => server.id === id) || null;
    }
  },
  
  // Create or update an MCP server
  createOrUpdateMCPServer: async (server: Partial<MCPServer>): Promise<MCPServer> => {
    try {
      const response = await axios.post(MCP_API.createOrUpdate, server);
      return response.data;
    } catch (error) {
      console.error('Error creating/updating MCP server:', error);
      
      // Fallback to mock data if API call fails
      console.warn('Falling back to mock data');
      
      if (server.id) {
        // Update existing server in mock data
        const updatedServer: MCPServer = {
          ...mockMCPServers.find(s => s.id === server.id) as MCPServer,
          ...server,
        };
        return updatedServer;
      } else {
        // Create new server in mock data
        const newServer: MCPServer = {
          ...(server as Omit<MCPServer, 'id'>),
          id: Math.random().toString(36).substring(2, 9),
        };
        return newServer;
      }
    }
  },
  
  // Delete an MCP server
  deleteMCPServer: async (id: string): Promise<boolean> => {
    try {
      await axios.delete(MCP_API.delete(id));
      return true;
    } catch (error) {
      console.error(`Error deleting MCP server with ID ${id}:`, error);
      // Fallback to mock behavior if API call fails
      console.warn('Falling back to mock behavior');
      return true;
    }
  },
};

export const chatAPI = {
  // Get list of chat records
  getChatRecords: async (): Promise<ChatRecord[]> => {
    try {
      const response = await axios.get(CHAT_API.listRecords);
      return response.data;
    } catch (error) {
      console.error('Error fetching chat records:', error);
      return [];
    }
  },
  
  // Get chat responses for a specific chat
  getChatResponses: async (chatId: string): Promise<ChatResponse[]> => {
    try {
      const response = await axios.get(CHAT_API.listResponses(chatId));
      return response.data;
    } catch (error) {
      console.error(`Error fetching chat responses for chat ID ${chatId}:`, error);
      return [];
    }
  },
  
  // Delete a chat record
  deleteChat: async (chatId: string): Promise<boolean> => {
    try {
      await axios.delete(CHAT_API.deleteChat(chatId));
      return true;
    } catch (error) {
      console.error(`Error deleting chat with ID ${chatId}:`, error);
      return false;
    }
  }
};

export const scheduleAPI = {
  // Get list of schedules
  getSchedules: async (): Promise<Schedule[]> => {
    try {
      const response = await axios.get(SCHEDULE_API.list);
      return response.data;
    } catch (error) {
      console.error('Error fetching schedules:', error);
      // Fallback to mock data if API call fails
      console.warn('Falling back to mock data');
      return mockSchedules;
    }
  },
  
  // Create a new schedule
  createSchedule: async (schedule: { agentId: string; cronExpression: string; user_message?: string }): Promise<Schedule> => {
    try {
      const response = await axios.post(SCHEDULE_API.create, schedule);
      return response.data;
    } catch (error) {
      console.error('Error creating schedule:', error);
      
      // Fallback to mock data if API call fails
      console.warn('Falling back to mock data');
      
      // Find the agent to get its name
      const agent = mockAgents.find(a => a.id === schedule.agentId);
      
      // Create a new schedule in mock data
      const newSchedule: Schedule = {
        id: Math.random().toString(36).substring(2, 9),
        agentId: schedule.agentId,
        agentName: agent?.display_name || 'Unknown Agent',
        cronExpression: schedule.cronExpression,
        status: 'ENABLED',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      
      return newSchedule;
    }
  },
  
  // Update an existing schedule
  updateSchedule: async (schedule: Schedule): Promise<Schedule> => {
    try {
      const response = await axios.put(SCHEDULE_API.update(schedule.id), schedule);
      return response.data;
    } catch (error) {
      console.error('Error updating schedule:', error);
      
      // Fallback to mock data if API call fails
      console.warn('Falling back to mock behavior');
      
      // Update the schedule's updatedAt timestamp
      const updatedSchedule: Schedule = {
        ...schedule,
        updatedAt: new Date().toISOString(),
      };
      
      return updatedSchedule;
    }
  },
  
  // Delete a schedule
  deleteSchedule: async (id: string): Promise<boolean> => {
    try {
      await axios.delete(SCHEDULE_API.delete(id));
      return true;
    } catch (error) {
      console.error(`Error deleting schedule with ID ${id}:`, error);
      // Fallback to mock behavior if API call fails
      console.warn('Falling back to mock behavior');
      return true;
    }
  },
};

export const agentAPI = {
  // Get list of agents
  getAgents: async (): Promise<Agent[]> => {
    try {
      const response = await axios.get(AGENT_API.list);
      return response.data;
    } catch (error) {
      console.error('Error fetching agents:', error);
      // Fallback to mock data if API call fails
      console.warn('Falling back to mock data');
      return mockAgents;
    }
  },
  
  // Create or update an agent
  createOrUpdateAgent: async (agent: Partial<Agent>): Promise<Agent> => {
    try {
      const response = await axios.post(AGENT_API.createOrUpdate, agent);
      return response.data;
    } catch (error) {
      console.error('Error creating/updating agent:', error);
      
      // Fallback to mock data if API call fails
      console.warn('Falling back to mock data');
      
      if (agent.id) {
        // Update existing agent in mock data
        const updatedAgent: Agent = {
          ...mockAgents.find(a => a.id === agent.id) as Agent,
          ...agent,
          updated_at: new Date().toISOString(),
        };
        return updatedAgent;
      } else {
        // Create new agent in mock data
        const newAgent: Agent = {
          ...(agent as Omit<Agent, 'id'>),
          id: Math.random().toString(36).substring(2, 9),
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        return newAgent;
      }
    }
  },
  
  // Get list of available tools
  getTools: async (): Promise<Tool[]> => {
    try {
      const response = await axios.get(AGENT_API.toolList);
      return response.data;
    } catch (error) {
      console.error('Error fetching tools:', error);
      // Fallback to mock data if API call fails
      console.warn('Falling back to mock data');
      return mockTools;
    }
  },

  deleteAgent: async (id: string): Promise<boolean> => {
    try {
      await axios.delete(AGENT_API.delete(id));
      return true;
    } catch (error) {
      console.error(`Error deleting agent with ID ${id}:`, error);
      // Fallback to mock behavior if API call fails
      console.warn('Falling back to mock behavior');
      return true;
    }
  },
  
  // Stream chat with an agent
  streamChat: (agentId: string, userMessage: string, chatRecordEnabled: boolean = true): Promise<Response> => {
    // Use fetch API to make a POST request with proper headers for SSE
    return fetch(AGENT_API.streamChat, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify({
        agent_id: agentId,
        user_message: userMessage,
        chat_record_enabled: chatRecordEnabled
      })
    });
  }
};
