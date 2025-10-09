from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class OrchestrationNode(BaseModel):
    """Model for orchestration nodes (agents or nested orchestrations)."""
    id: str
    type: str  # 'agent' or 'orchestration'
    name: str
    displayName: str
    description: str
    position: Dict[str, float]
    agentId: Optional[str] = None
    orchestrationId: Optional[str] = None
    agentConfig: Optional[Dict[str, Any]] = None
    orchestrationConfig: Optional[Dict[str, Any]] = None

class OrchestrationEdge(BaseModel):
    """Model for orchestration edges (connections between nodes)."""
    id: str
    source: str
    target: str
    condition: Optional[str] = None
    label: Optional[str] = None

class OrchestrationConfig(BaseModel):
    """Model for orchestration configuration."""
    id: Optional[str] = None
    name: str
    displayName: str
    description: str
    type: str  # 'swarm', 'graph', 'workflow', 'agent_as_tool'
    nodes: List[OrchestrationNode]
    edges: List[OrchestrationEdge]
    
    # Common configuration
    executionTimeout: Optional[int] = 900
    
    # Swarm-specific configuration
    entryPoint: Optional[str] = None
    maxHandoffs: Optional[int] = 20
    maxIterations: Optional[int] = 20
    nodeTimeout: Optional[int] = 300
    repetitiveHandoffDetectionWindow: Optional[int] = 0
    repetitiveHandoffMinUniqueAgents: Optional[int] = 0
    
    # Graph-specific configuration
    maxNodeExecutions: Optional[int] = None
    resetOnRevisit: Optional[bool] = None
    
    # Workflow-specific configuration
    parallelExecution: Optional[bool] = None
    taskPriorities: Optional[Dict[str, int]] = None
    
    # Agent as Tool-specific configuration
    orchestratorAgent: Optional[str] = None
    toolAgents: Optional[List[str]] = None
    
    # Additional metadata
    userId: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

class OrchestrationExecution(BaseModel):
    """Model for orchestration execution tracking."""
    id: Optional[str] = None
    orchestrationId: str
    userId: str
    status: str  # 'pending', 'running', 'completed', 'failed'
    startTime: str
    endTime: Optional[str] = None
    inputMessage: str
    results: Optional[Dict[str, Any]] = None
    nodeHistory: Optional[List[Dict[str, Any]]] = None
    errorMessage: Optional[str] = None

class ExecutionRequest(BaseModel):
    """Model for orchestration execution request."""
    inputMessage: str
    chatRecordEnabled: Optional[bool] = True

class ExecutionResponse(BaseModel):
    """Model for orchestration execution response."""
    executionId: str
    status: str
    message: str
