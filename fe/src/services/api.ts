import axios from 'axios';

// Base URL for API calls using Vite proxy
const BASE_URL = '/api';

// User API endpoints
const USER_API = {
  register: `${BASE_URL}/user/register`,
  login: `${BASE_URL}/user/login`,
  logout: `${BASE_URL}/user/logout`,
  me: `${BASE_URL}/user/me`,
  updateMe: `${BASE_URL}/user/me`,
  changePassword: `${BASE_URL}/user/change-password`,
  verifyToken: `${BASE_URL}/user/verify-token`,
  list: `${BASE_URL}/user/list`,
  get: (id: string) => `${BASE_URL}/user/${id}`,
  update: (id: string) => `${BASE_URL}/user/${id}`,
  delete: (id: string) => `${BASE_URL}/user/${id}`,
};

// Agent API endpoints
const AGENT_API = {
  list: `${BASE_URL}/agent/list`,
  createOrUpdate: `${BASE_URL}/agent/createOrUpdate`,
  toolList: `${BASE_URL}/agent/tool_list`,
  delete: (id: string) => `${BASE_URL}/agent/delete/${id}`,
  streamChat: `${BASE_URL}/agent/stream_chat`,
};

// File API endpoints
const FILE_API = {
  upload: `${BASE_URL}/files/upload`,
  download: (s3Key: string) => `${BASE_URL}/files/download/${encodeURIComponent(s3Key)}`,
  downloadPost: `${BASE_URL}/files/download`,
  info: (fileId: string) => `${BASE_URL}/files/info/${fileId}`,
  delete: (fileId: string) => `${BASE_URL}/files/${fileId}`,
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

// Orchestration API endpoints
const ORCHESTRATION_API = {
  list: `${BASE_URL}/orchestration/list`,
  create: `${BASE_URL}/orchestration/create`,
  get: (id: string) => `${BASE_URL}/orchestration/${id}`,
  update: (id: string) => `${BASE_URL}/orchestration/${id}`,
  delete: (id: string) => `${BASE_URL}/orchestration/${id}`,
  execute: (id: string) => `${BASE_URL}/orchestration/${id}/execute`,
  executionStatus: (executionId: string) => `${BASE_URL}/orchestration/execution/${executionId}/status`,
  stopExecution: (executionId: string) => `${BASE_URL}/orchestration/execution/${executionId}/stop`,
};

// Configuration API endpoints
const CONFIG_API = {
  list: `${BASE_URL}/config/list`,
  create: `${BASE_URL}/config/create`,
  get: (key: string) => `${BASE_URL}/config/get/${key}`,
  update: (key: string) => `${BASE_URL}/config/update/${key}`,
  delete: (key: string) => `${BASE_URL}/config/delete/${key}`,
  listByParent: (parent: string) => `${BASE_URL}/config/list/${parent}`,
  rootCategories: `${BASE_URL}/config/root-categories`,
  categoryTree: `${BASE_URL}/config/category-tree`,
  modelProvider: `${BASE_URL}/config/model-provider`,
  initDefaultCategories: `${BASE_URL}/config/init-default-categories`,
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
  'us.anthropic.claude-opus-4-20250514-v1:0',
  'us.anthropic.claude-sonnet-4-20250514-v1:0',
  'us.anthropic.claude-3-7-sonnet-20250219-v1:0',
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

// Configuration interfaces
export interface SystemConfig {
  key: string;
  value: string;
  key_display_name?: string;
  type: string; // 'category' or 'item'
  seq_num: number;
  parent?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ConfigCategory {
  key: string;
  key_display_name?: string;
  parent?: string;
  children: ConfigCategory[];
  configs: SystemConfig[];
}

export interface CreateConfigRequest {
  key: string;
  value: string;
  key_display_name?: string;
  type: string;
  seq_num: number;
  parent?: string;
}

export interface UpdateConfigRequest {
  value?: string;
  key_display_name?: string;
  type?: string;
  seq_num?: number;
  parent?: string;
}

export interface ConfigResponse {
  success: boolean;
  message: string;
  data?: SystemConfig;
}

export interface ConfigListResponse {
  success: boolean;
  message: string;
  data: SystemConfig[];
}

export interface CategoryTreeResponse {
  success: boolean;
  message: string;
  data: ConfigCategory[];
}

export interface ModelProviderConfig {
  model_id: string;
  temperature: number;
  top_p: number;
  max_tokens: number;
  api_base_url?: string;
  api_key?: string;
}

export interface ModelProviderRequest {
  provider_key: string;
  provider_display_name: string;
  config: ModelProviderConfig;
}

// Orchestration interfaces
export interface OrchestrationConfig {
  id: string;
  name: string;
  displayName: string;
  description: string;
  type: string; // 'swarm', 'graph', 'workflow', 'agent_as_tool'
  nodes: OrchestrationNode[];
  edges: OrchestrationEdge[];
  
  // Common configuration
  executionTimeout?: number;
  
  // Swarm-specific configuration
  entryPoint?: string;
  maxHandoffs?: number;
  maxIterations?: number;
  nodeTimeout?: number;
  repetitiveHandoffDetectionWindow?: number;
  repetitiveHandoffMinUniqueAgents?: number;
  
  // Graph-specific configuration
  maxNodeExecutions?: number;
  resetOnRevisit?: boolean;
  
  // Workflow-specific configuration
  parallelExecution?: boolean;
  taskPriorities?: Record<string, number>;
  
  // Agent as Tool-specific configuration
  orchestratorAgent?: string;
  toolAgents?: string[];
  
  // Additional metadata
  userId?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface OrchestrationNode {
  id: string;
  type: string; // 'agent' or 'orchestration'
  name: string;
  displayName: string;
  description: string;
  position: { x: number; y: number };
  agentId?: string;
  orchestrationId?: string;
  agentConfig?: any;
  orchestrationConfig?: any;
}

export interface OrchestrationEdge {
  id: string;
  source: string;
  target: string;
  condition?: string;
  label?: string;
}

export interface OrchestrationExecution {
  id: string;
  orchestrationId: string;
  userId: string;
  status: string; // 'pending', 'running', 'completed', 'failed'
  startTime: string;
  endTime?: string;
  inputMessage: string;
  results?: Record<string, any>;
  nodeHistory?: Array<{
    nodeId: string;
    status: string;
    executionTime: number;
    result?: any;
  }>;
  errorMessage?: string;
}

export interface ExecutionRequest {
  inputMessage: string;
  chatRecordEnabled?: boolean;
}

export interface ExecutionResponse {
  executionId: string;
  status: string;
  message: string;
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

// User interfaces
export interface UserRegister {
  username: string;
  email?: string;
  password: string;
}

export interface UserLogin {
  username: string;
  password: string;
}

export interface UserInfo {
  user_id: string;
  username: string;
  email?: string;
  status: string;
}

export interface AuthResponse {
  message: string;
  user: UserInfo;
  access_token: string;
  token_type: string;
}

// Create axios instance with interceptors for authentication
const createAuthenticatedAxios = () => {
  const instance = axios.create();
  
  // Request interceptor to add auth token
  instance.interceptors.request.use(
    (config) => {
      const token = localStorage.getItem('user-storage');
      if (token) {
        try {
          const parsed = JSON.parse(token);
          if (parsed.state?.token) {
            config.headers.Authorization = `Bearer ${parsed.state.token}`;
          }
        } catch (error) {
          console.error('Error parsing stored token:', error);
        }
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );
  
  // Response interceptor to handle auth errors
  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        // Token expired or invalid, clear storage and redirect to login
        localStorage.removeItem('user-storage');
        // Use window.location.replace to avoid back button issues
        window.location.replace('/login');
      }
      return Promise.reject(error);
    }
  );
  
  return instance;
};

// Create authenticated axios instance
const authAxios = createAuthenticatedAxios();

// Update all existing API calls to use authenticated axios
const createAuthenticatedAPI = () => {
  // Override the default axios instance for all API calls
  const originalAxios = axios.create();
  
  // Add the same interceptors to the original axios instance
  originalAxios.interceptors.request.use(
    (config) => {
      const token = localStorage.getItem('user-storage');
      if (token) {
        try {
          const parsed = JSON.parse(token);
          if (parsed.state?.token) {
            config.headers.Authorization = `Bearer ${parsed.state.token}`;
          }
        } catch (error) {
          console.error('Error parsing stored token:', error);
        }
      }
      return config;
    },
    (error) => Promise.reject(error)
  );
  
  originalAxios.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        localStorage.removeItem('user-storage');
        window.location.replace('/login');
      }
      return Promise.reject(error);
    }
  );
  
  return originalAxios;
};

// Use authenticated axios for all API calls
const apiAxios = createAuthenticatedAPI();

// User API functions
export const userAPI = {
  // Register a new user
  register: async (userData: UserRegister): Promise<AuthResponse> => {
    try {
      const response = await axios.post(USER_API.register, userData);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Registration failed');
    }
  },
  
  // Login user
  login: async (loginData: UserLogin): Promise<AuthResponse> => {
    try {
      const response = await axios.post(USER_API.login, loginData);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Login failed');
    }
  },
  
  // Logout user
  logout: async (): Promise<{ message: string }> => {
    try {
      const response = await authAxios.post(USER_API.logout);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Logout failed');
    }
  },
  
  // Get current user info
  getCurrentUser: async (): Promise<{ user: UserInfo }> => {
    try {
      const response = await authAxios.get(USER_API.me);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get user info');
    }
  },
  
  // Update current user
  updateCurrentUser: async (userData: { email?: string; status?: string }): Promise<{ message: string; user: UserInfo }> => {
    try {
      const response = await authAxios.put(USER_API.updateMe, userData);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to update user');
    }
  },
  
  // Change password
  changePassword: async (passwordData: { old_password: string; new_password: string }): Promise<{ message: string }> => {
    try {
      const response = await authAxios.post(USER_API.changePassword, passwordData);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to change password');
    }
  },
  
  // Verify token
  verifyToken: async (): Promise<{ valid: boolean; user: UserInfo }> => {
    try {
      const response = await authAxios.get(USER_API.verifyToken);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Token verification failed');
    }
  },
  
  // Admin functions
  listUsers: async (limit: number = 100): Promise<UserInfo[]> => {
    try {
      const response = await authAxios.get(`${USER_API.list}?limit=${limit}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to list users');
    }
  },
  
  getUserById: async (userId: string): Promise<{ user: UserInfo }> => {
    try {
      const response = await authAxios.get(USER_API.get(userId));
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get user');
    }
  },
  
  updateUserById: async (userId: string, userData: { email?: string; status?: string }): Promise<{ message: string; user: UserInfo }> => {
    try {
      const response = await authAxios.put(USER_API.update(userId), userData);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to update user');
    }
  },
  
  deleteUserById: async (userId: string): Promise<{ message: string }> => {
    try {
      const response = await authAxios.delete(USER_API.delete(userId));
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to delete user');
    }
  }
};

// API functions
export const mcpAPI = {
  // Get list of MCP servers
  getMCPServers: async (): Promise<MCPServer[]> => {
    try {
      const response = await apiAxios.get(MCP_API.list);
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
      const response = await apiAxios.get(MCP_API.get(id));
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
      const response = await apiAxios.post(MCP_API.createOrUpdate, server);
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
      await apiAxios.delete(MCP_API.delete(id));
      return true;
    } catch (error) {
      console.error(`Error deleting MCP server with ID ${id}:`, error);
      // Fallback to mock behavior if API call fails
      console.warn('Falling back to mock behavior');
      return true;
    }
  },
};

export const configAPI = {
  // Get category tree
  getCategoryTree: async (): Promise<CategoryTreeResponse> => {
    try {
      const response = await apiAxios.get(CONFIG_API.categoryTree);
      return response.data;
    } catch (error) {
      console.error('Error fetching category tree:', error);
      throw new Error('Failed to fetch category tree');
    }
  },
  
  // Get configs by parent
  getConfigsByParent: async (parent: string): Promise<ConfigListResponse> => {
    try {
      const response = await apiAxios.get(CONFIG_API.listByParent(parent));
      return response.data;
    } catch (error) {
      console.error(`Error fetching configs for parent ${parent}:`, error);
      throw new Error('Failed to fetch configs');
    }
  },
  
  // Get all configs
  getAllConfigs: async (): Promise<ConfigListResponse> => {
    try {
      const response = await apiAxios.get(CONFIG_API.list);
      return response.data;
    } catch (error) {
      console.error('Error fetching all configs:', error);
      throw new Error('Failed to fetch configs');
    }
  },
  
  // Get specific config
  getConfig: async (key: string): Promise<ConfigResponse> => {
    try {
      const response = await apiAxios.get(CONFIG_API.get(key));
      return response.data;
    } catch (error) {
      console.error(`Error fetching config ${key}:`, error);
      throw new Error('Failed to fetch config');
    }
  },
  
  // Create config
  createConfig: async (config: CreateConfigRequest): Promise<ConfigResponse> => {
    try {
      const response = await apiAxios.post(CONFIG_API.create, config);
      return response.data;
    } catch (error) {
      console.error('Error creating config:', error);
      throw new Error('Failed to create config');
    }
  },
  
  // Update config
  updateConfig: async (key: string, config: UpdateConfigRequest): Promise<ConfigResponse> => {
    try {
      const response = await apiAxios.put(CONFIG_API.update(key), config);
      return response.data;
    } catch (error) {
      console.error(`Error updating config ${key}:`, error);
      throw new Error('Failed to update config');
    }
  },
  
  // Delete config
  deleteConfig: async (key: string): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await apiAxios.delete(CONFIG_API.delete(key));
      return response.data;
    } catch (error) {
      console.error(`Error deleting config ${key}:`, error);
      throw new Error('Failed to delete config');
    }
  },
  
  // Get root categories
  getRootCategories: async (): Promise<ConfigListResponse> => {
    try {
      const response = await apiAxios.get(CONFIG_API.rootCategories);
      return response.data;
    } catch (error) {
      console.error('Error fetching root categories:', error);
      throw new Error('Failed to fetch root categories');
    }
  },
  
  // Create model provider
  createModelProvider: async (provider: ModelProviderRequest): Promise<ConfigResponse> => {
    try {
      const response = await apiAxios.post(CONFIG_API.modelProvider, provider);
      return response.data;
    } catch (error) {
      console.error('Error creating model provider:', error);
      throw new Error('Failed to create model provider');
    }
  },
  
  // Initialize default categories
  initDefaultCategories: async (): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await apiAxios.post(CONFIG_API.initDefaultCategories);
      return response.data;
    } catch (error) {
      console.error('Error initializing default categories:', error);
      throw new Error('Failed to initialize default categories');
    }
  }
};

export const chatAPI = {
  // Get list of chat records
  getChatRecords: async (): Promise<ChatRecord[]> => {
    try {
      const response = await apiAxios.get(CHAT_API.listRecords);
      return response.data;
    } catch (error) {
      console.error('Error fetching chat records:', error);
      return [];
    }
  },
  
  // Get chat responses for a specific chat
  getChatResponses: async (chatId: string): Promise<ChatResponse[]> => {
    try {
      const response = await apiAxios.get(CHAT_API.listResponses(chatId));
      return response.data;
    } catch (error) {
      console.error(`Error fetching chat responses for chat ID ${chatId}:`, error);
      return [];
    }
  },
  // Delete a chat record
  deleteChat: async (chatId: string): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await apiAxios.delete(CHAT_API.deleteChat(chatId));
      
      // Check if the response contains a success message
      if (response.data && response.data.message) {
        return { success: true, message: response.data.message };
      }
      // Check if the response contains an error
      else if (response.data && response.data.error) {
        return { success: false, message: response.data.error };
      }
      // Default success case
      else {
        return { success: true, message: 'Chat deleted successfully' };
      }
    } catch (error: any) {
      console.error(`Error deleting chat with ID ${chatId}:`, error);
      
      // Try to extract error message from response
      const errorMessage = error.response?.data?.error || 
                          error.response?.data?.detail || 
                          error.message || 
                          'Failed to delete chat';
      
      return { success: false, message: errorMessage };
    }
  }
};

export const scheduleAPI = {
  // Get list of schedules
  getSchedules: async (): Promise<Schedule[]> => {
    try {
      const response = await apiAxios.get(SCHEDULE_API.list);
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
      const response = await apiAxios.post(SCHEDULE_API.create, schedule);
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
      const response = await apiAxios.put(SCHEDULE_API.update(schedule.id), schedule);
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
      await apiAxios.delete(SCHEDULE_API.delete(id));
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
      const response = await apiAxios.get(AGENT_API.list);
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
      const response = await apiAxios.post(AGENT_API.createOrUpdate, agent);
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
      const response = await apiAxios.get(AGENT_API.toolList);
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
      await apiAxios.delete(AGENT_API.delete(id));
      return true;
    } catch (error) {
      console.error(`Error deleting agent with ID ${id}:`, error);
      // Fallback to mock behavior if API call fails
      console.warn('Falling back to mock behavior');
      return true;
    }
  },
  
  // Stream chat with an agent
  streamChat: (agentId: string, userMessage: string, chatRecordEnabled: boolean = true, chatRecordId?: string, fileAttachments?: any[]): Promise<Response> => {
    // Get token for SSE request
    const token = localStorage.getItem('user-storage');
    // console.log('Retrieved token from localStorage:', token);
    let authToken = '';
    if (token) {
      try {
        const parsed = JSON.parse(token);
        if (parsed.state?.token) {
          authToken = parsed.state.token;
        }
      } catch (error) {
        console.error('Error parsing stored token:', error);
      }
    }
    
    // Prepare request body
    const requestBody: any = {
      agent_id: agentId,
      user_message: userMessage,
      chat_record_enabled: chatRecordEnabled
    };
    
    // Add chat_record_id if provided for continuing conversation
    if (chatRecordId) {
      requestBody.chat_record_id = chatRecordId;
    }
    
    // Add file attachments if provided
    if (fileAttachments && fileAttachments.length > 0) {
      requestBody.file_attachments = fileAttachments;
    }
    
    // Use fetch API to make a POST request with proper headers for SSE
    return fetch(AGENT_API.streamChat, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        'Authorization': authToken ? `Bearer ${authToken}` : '',
      },
      body: JSON.stringify(requestBody)
    });
  }
};

export const fileAPI = {
  // Upload files
  uploadFiles: async (files: File[]): Promise<{ files: any[] }> => {
    try {
      const formData = new FormData();
      files.forEach(file => {
        formData.append('files', file);
      });
      
      const response = await apiAxios.post(FILE_API.upload, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      console.error('Error uploading files:', error);
      if (axios.isAxiosError(error) && error.response?.data?.detail) {
        console.log(`----------------${error.response.data.detail}`);
        throw new Error(error.response.data.detail);
      } else {
        throw new Error('Failed to upload files');
      }
    }
  },
  
  // Download a file using POST request to avoid URL encoding issues
  downloadFile: async (s3Key: string): Promise<Blob> => {
    try {
      const response = await apiAxios.post(FILE_API.downloadPost, {
        s3_key: s3Key
      }, {
        responseType: 'blob',
      });
      return response.data;
    } catch (error) {
      console.error(`Error downloading file ${s3Key}:`, error);
      throw new Error('Failed to download file');
    }
  },
  
  // Delete a file
  deleteFile: async (fileId: string): Promise<boolean> => {
    try {
      await apiAxios.delete(FILE_API.delete(fileId));
      return true;
    } catch (error) {
      console.error(`Error deleting file ${fileId}:`, error);
      throw new Error('Failed to delete file');
    }
  },
  
  // Get file info
  getFileInfo: async (fileId: string): Promise<any> => {
    try {
      const response = await apiAxios.get(FILE_API.info(fileId));
      return response.data;
    } catch (error) {
      console.error(`Error getting file info ${fileId}:`, error);
      throw new Error('Failed to get file info');
    }
  },
  
  // Generate download URL for S3 key
  getDownloadUrl: (s3Key: string): string => {
    return FILE_API.download(s3Key);
  },
};

export const orchestrationAPI = {
  // Get list of orchestrations
  getOrchestrations: async (): Promise<OrchestrationConfig[]> => {
    try {
      const response = await apiAxios.get(ORCHESTRATION_API.list);
      return response.data;
    } catch (error) {
      console.error('Error fetching orchestrations:', error);
      throw new Error('Failed to fetch orchestrations');
    }
  },
  
  // Get a specific orchestration
  getOrchestration: async (id: string): Promise<OrchestrationConfig> => {
    try {
      const response = await apiAxios.get(ORCHESTRATION_API.get(id));
      return response.data;
    } catch (error) {
      console.error(`Error fetching orchestration with ID ${id}:`, error);
      throw new Error('Failed to fetch orchestration');
    }
  },
  
  // Create a new orchestration
  createOrchestration: async (config: Partial<OrchestrationConfig>): Promise<OrchestrationConfig> => {
    try {
      const response = await apiAxios.post(ORCHESTRATION_API.create, config);
      return response.data;
    } catch (error) {
      console.error('Error creating orchestration:', error);
      throw new Error('Failed to create orchestration');
    }
  },
  
  // Update an existing orchestration
  updateOrchestration: async (id: string, config: Partial<OrchestrationConfig>): Promise<OrchestrationConfig> => {
    try {
      const response = await apiAxios.put(ORCHESTRATION_API.update(id), config);
      return response.data;
    } catch (error) {
      console.error('Error updating orchestration:', error);
      throw new Error('Failed to update orchestration');
    }
  },
  
  // Delete an orchestration
  deleteOrchestration: async (id: string): Promise<boolean> => {
    try {
      await apiAxios.delete(ORCHESTRATION_API.delete(id));
      return true;
    } catch (error) {
      console.error(`Error deleting orchestration with ID ${id}:`, error);
      throw new Error('Failed to delete orchestration');
    }
  },
  
  // Execute an orchestration
  executeOrchestration: async (id: string, request: ExecutionRequest): Promise<ExecutionResponse> => {
    try {
      const response = await apiAxios.post(ORCHESTRATION_API.execute(id), request);
      return response.data;
    } catch (error) {
      console.error('Error executing orchestration:', error);
      throw new Error('Failed to execute orchestration');
    }
  },
  
  // Get execution status
  getExecutionStatus: async (executionId: string): Promise<OrchestrationExecution> => {
    try {
      const response = await apiAxios.get(ORCHESTRATION_API.executionStatus(executionId));
      return response.data;
    } catch (error) {
      console.error(`Error fetching execution status for ${executionId}:`, error);
      throw new Error('Failed to get execution status');
    }
  },
  
  // Stop execution
  stopExecution: async (executionId: string): Promise<boolean> => {
    try {
      await apiAxios.post(ORCHESTRATION_API.stopExecution(executionId));
      return true;
    } catch (error) {
      console.error(`Error stopping execution ${executionId}:`, error);
      throw new Error('Failed to stop execution');
    }
  },
  
  // List executions
  listExecutions: async (orchestrationId?: string): Promise<OrchestrationExecution[]> => {
    try {
      const url = orchestrationId 
        ? `/orchestration/executions?orchestrationId=${orchestrationId}`
        : '/orchestration/executions';
      const response = await apiAxios.get(url);
      return response.data;
    } catch (error) {
      console.error('Error listing executions:', error);
      throw new Error('Failed to list executions');
    }
  },
};
