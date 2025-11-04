// Multi-Agent Orchestration Types
export const OrchestrationType = {
  SWARM: 'swarm',
  GRAPH: 'graph', 
  WORKFLOW: 'workflow',
  AGENT_AS_TOOL: 'agents_as_tools'
} as const;

export type OrchestrationType = typeof OrchestrationType[keyof typeof OrchestrationType];

export const NodeType = {
  AGENT: 'agent',
  ORCHESTRATION: 'orchestration'
} as const;

export type NodeType = typeof NodeType[keyof typeof NodeType];

// Base Node Interface
export interface BaseNode {
  id: string;
  type: NodeType;
  name: string;
  displayName: string;
  description: string;
  position: { x: number; y: number };
}

// Agent Node
export interface AgentNode extends BaseNode {
  type: 'agent';
  agentId?: string; // existing agent
  agentConfig?: Partial<Agent>; // new agent config
}

// Orchestration Node  
export interface OrchestrationNode extends BaseNode {
  type: 'orchestration';
  orchestrationId?: string; // existing orchestration
  orchestrationConfig?: OrchestrationConfig; // nested orchestration
}

// Edge for connections
export interface OrchestrationEdge {
  id: string;
  source: string;
  target: string;
  condition?: string; // for conditional edges
  label?: string;
}

// Orchestration Configuration
export interface OrchestrationConfig {
  id: string;
  name: string;
  displayName: string;
  description: string;
  type: OrchestrationType;
  nodes: (AgentNode | OrchestrationNode)[];
  edges: OrchestrationEdge[];
  
  // Common configuration
  executionTimeout?: number; // Total execution timeout in seconds (default: 900)
  
  // Swarm-specific configuration
  entryPoint?: string; // Agent instance to start with (required for swarm)
  maxHandoffs?: number; // Maximum number of agent handoffs (default: 20)
  maxIterations?: number; // Maximum total iterations (default: 20)
  nodeTimeout?: number; // Individual agent timeout in seconds (default: 300)
  repetitiveHandoffDetectionWindow?: number; // Number of recent nodes to check (default: 0)
  repetitiveHandoffMinUniqueAgents?: number; // Minimum unique nodes required (default: 0)
  
  // Graph-specific configuration
  maxNodeExecutions?: number; // Limit total node executions for cyclic graphs
  resetOnRevisit?: boolean; // Control whether nodes reset state when revisited
  
  // Workflow-specific configuration
  parallelExecution?: boolean; // Enable/disable parallel task execution
  taskPriorities?: Record<string, number>; // Priority levels for task execution
  
  // Agent as Tool-specific configuration
  orchestratorAgent?: string; // The primary agent that coordinates other agents (required)
  toolAgents?: string[]; // List of specialized agents available as tools
  
  // Legacy field for backward compatibility
  extras?: Record<string, any>; // Additional type-specific configurations
}

// Execution Result
export interface OrchestrationExecution {
  id: string;
  orchestrationId: string;
  userId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
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

// API Request/Response types
export interface ExecutionRequest {
  inputMessage: string;
  chatRecordEnabled?: boolean;
}

export interface ExecutionResponse {
  executionId: string;
  status: string;
  message: string;
}

// ReactFlow Node Data
export interface ReactFlowNodeData {
  label: string;
  nodeType: NodeType;
  agentId?: string;
  orchestrationId?: string;
  config?: any;
}

// Import Agent type from services
import type { Agent } from '../services/api';
