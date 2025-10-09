import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { 
  orchestrationAPI,
  type OrchestrationConfig,
  type OrchestrationExecution,
  type OrchestrationNode,
  type OrchestrationEdge,
  type ExecutionRequest,
} from '../services/api';
import type { 
  AgentNode, 
  BaseNode
} from '../types/orchestration';

interface OrchestrationStore {
  // Orchestration management
  orchestrations: OrchestrationConfig[];
  currentOrchestration: OrchestrationConfig | null;
  loading: boolean;
  
  // Editor state
  nodes: (AgentNode | OrchestrationNode)[];
  edges: OrchestrationEdge[];
  selectedNode: string | null;
  selectedEdge: string | null;
  
  // Execution state
  executions: OrchestrationExecution[];
  currentExecution: OrchestrationExecution | null;
  executionLoading: boolean;
  
  // Modal states
  createModalVisible: boolean;
  editModalVisible: boolean;
  nodeEditorVisible: boolean;
  edgeEditorVisible: boolean;
  executionModalVisible: boolean;
  
  // Actions - Orchestration CRUD
  setLoading: (loading: boolean) => void;
  fetchOrchestrations: () => Promise<void>;
  createOrchestration: (config: Partial<OrchestrationConfig>) => Promise<void>;
  updateOrchestration: (id: string, config: Partial<OrchestrationConfig>) => Promise<void>;
  deleteOrchestration: (id: string) => Promise<void>;
  setCurrentOrchestration: (orchestration: OrchestrationConfig | null) => void;
  
  // Actions - Editor
  addNode: (node: AgentNode | OrchestrationNode) => void;
  updateNode: (id: string, updates: Partial<BaseNode>) => void;
  deleteNode: (id: string) => void;
  addEdge: (edge: OrchestrationEdge) => void;
  updateEdge: (id: string, updates: Partial<OrchestrationEdge>) => void;
  deleteEdge: (id: string) => void;
  setSelectedNode: (nodeId: string | null) => void;
  setSelectedEdge: (edgeId: string | null) => void;
  clearSelection: () => void;
  
  // Actions - Execution
  executeOrchestration: (id: string, request: ExecutionRequest) => Promise<void>;
  stopExecution: (executionId: string) => Promise<void>;
  getExecutionStatus: (executionId: string) => Promise<void>;
  fetchExecutions: (orchestrationId?: string) => Promise<void>;
  setCurrentExecution: (execution: OrchestrationExecution | null) => void;
  
  // Actions - Modal management
  setCreateModalVisible: (visible: boolean) => void;
  setEditModalVisible: (visible: boolean) => void;
  setNodeEditorVisible: (visible: boolean) => void;
  setEdgeEditorVisible: (visible: boolean) => void;
  setExecutionModalVisible: (visible: boolean) => void;
  
  // Actions - Utility
  resetEditor: () => void;
  loadOrchestrationToEditor: (orchestration: OrchestrationConfig) => void;
  saveEditorToOrchestration: () => OrchestrationConfig | null;
}


export const useOrchestrationStore = create<OrchestrationStore>()(
  devtools(
    (set, get) => ({
      // Initial state
      orchestrations: [],
      currentOrchestration: null,
      loading: false,
      
      nodes: [],
      edges: [],
      selectedNode: null,
      selectedEdge: null,
      
      executions: [],
      currentExecution: null,
      executionLoading: false,
      
      createModalVisible: false,
      editModalVisible: false,
      nodeEditorVisible: false,
      edgeEditorVisible: false,
      executionModalVisible: false,
      
      // Orchestration CRUD actions
      setLoading: (loading) => set({ loading }),
      
      fetchOrchestrations: async () => {
        set({ loading: true });
        try {
          const orchestrations = await orchestrationAPI.getOrchestrations();
          set({ orchestrations });
        } catch (error) {
          console.error('Failed to fetch orchestrations:', error);
        } finally {
          set({ loading: false });
        }
      },
      
      createOrchestration: async (config) => {
        set({ loading: true });
        try {
          const newOrchestration = await orchestrationAPI.createOrchestration(config);
          set(state => ({
            orchestrations: [...state.orchestrations, newOrchestration],
            createModalVisible: false
          }));
        } catch (error) {
          console.error('Failed to create orchestration:', error);
        } finally {
          set({ loading: false });
        }
      },
      
      updateOrchestration: async (id, config) => {
        set({ loading: true });
        try {
          const updatedOrchestration = await orchestrationAPI.updateOrchestration(id, config);
          set(state => ({
            orchestrations: state.orchestrations.map(o => 
              o.id === id ? updatedOrchestration : o
            ),
            currentOrchestration: state.currentOrchestration?.id === id 
              ? updatedOrchestration 
              : state.currentOrchestration,
            editModalVisible: false
          }));
        } catch (error) {
          console.error('Failed to update orchestration:', error);
        } finally {
          set({ loading: false });
        }
      },
      
      deleteOrchestration: async (id) => {
        set({ loading: true });
        try {
          await orchestrationAPI.deleteOrchestration(id);
          set(state => ({
            orchestrations: state.orchestrations.filter(o => o.id !== id),
            currentOrchestration: state.currentOrchestration?.id === id 
              ? null 
              : state.currentOrchestration
          }));
        } catch (error) {
          console.error('Failed to delete orchestration:', error);
        } finally {
          set({ loading: false });
        }
      },
      
      setCurrentOrchestration: (orchestration) => set({ currentOrchestration: orchestration }),
      
      // Editor actions
      addNode: (node) => set(state => ({ nodes: [...state.nodes, node] })),
      
      updateNode: (id, updates) => set(state => ({
        nodes: state.nodes.map(node => 
          node.id === id ? { ...node, ...updates } : node
        )
      })),
      
      deleteNode: (id) => set(state => ({
        nodes: state.nodes.filter(node => node.id !== id),
        edges: state.edges.filter(edge => edge.source !== id && edge.target !== id),
        selectedNode: state.selectedNode === id ? null : state.selectedNode
      })),
      
      addEdge: (edge) => set(state => ({ edges: [...state.edges, edge] })),
      
      updateEdge: (id, updates) => set(state => ({
        edges: state.edges.map(edge => 
          edge.id === id ? { ...edge, ...updates } : edge
        )
      })),
      
      deleteEdge: (id) => set(state => ({
        edges: state.edges.filter(edge => edge.id !== id),
        selectedEdge: state.selectedEdge === id ? null : state.selectedEdge
      })),
      
      setSelectedNode: (nodeId) => set({ selectedNode: nodeId, selectedEdge: null }),
      setSelectedEdge: (edgeId) => set({ selectedEdge: edgeId, selectedNode: null }),
      clearSelection: () => set({ selectedNode: null, selectedEdge: null }),
      
      // Execution actions
      executeOrchestration: async (id, request) => {
        set({ executionLoading: true });
        try {
          const response = await orchestrationAPI.executeOrchestration(id, request);
          // Fetch the execution status
          const execution = await orchestrationAPI.getExecutionStatus(response.executionId);
          set(state => ({
            executions: [...state.executions, execution],
            currentExecution: execution
          }));
        } catch (error) {
          console.error('Failed to execute orchestration:', error);
        } finally {
          set({ executionLoading: false });
        }
      },
      
      stopExecution: async (executionId) => {
        try {
          await orchestrationAPI.stopExecution(executionId);
          set(state => ({
            executions: state.executions.map(exec => 
              exec.id === executionId ? { ...exec, status: 'failed' as const } : exec
            ),
            currentExecution: state.currentExecution?.id === executionId 
              ? { ...state.currentExecution, status: 'failed' as const }
              : state.currentExecution
          }));
        } catch (error) {
          console.error('Failed to stop execution:', error);
        }
      },
      
      getExecutionStatus: async (executionId) => {
        try {
          const execution = await orchestrationAPI.getExecutionStatus(executionId);
          set(state => ({
            executions: state.executions.map(exec => 
              exec.id === executionId ? execution : exec
            ),
            currentExecution: state.currentExecution?.id === executionId 
              ? execution 
              : state.currentExecution
          }));
        } catch (error) {
          console.error('Failed to get execution status:', error);
        }
      },
      
      fetchExecutions: async (orchestrationId) => {
        try {
          const executions = await orchestrationAPI.listExecutions(orchestrationId);
          set({ executions });
        } catch (error) {
          console.error('Failed to fetch executions:', error);
        }
      },
      
      setCurrentExecution: (execution) => set({ currentExecution: execution }),
      
      // Modal actions
      setCreateModalVisible: (visible) => set({ createModalVisible: visible }),
      setEditModalVisible: (visible) => set({ editModalVisible: visible }),
      setNodeEditorVisible: (visible) => set({ nodeEditorVisible: visible }),
      setEdgeEditorVisible: (visible) => set({ edgeEditorVisible: visible }),
      setExecutionModalVisible: (visible) => set({ executionModalVisible: visible }),
      
      // Utility actions
      resetEditor: () => set({ 
        nodes: [], 
        edges: [], 
        selectedNode: null, 
        selectedEdge: null 
      }),
      
      loadOrchestrationToEditor: (orchestration) => set({
        nodes: orchestration.nodes,
        edges: orchestration.edges,
        currentOrchestration: orchestration,
        selectedNode: null,
        selectedEdge: null
      }),
      
      saveEditorToOrchestration: () => {
        const state = get();
        if (!state.currentOrchestration) return null;
        
        return {
          ...state.currentOrchestration,
          nodes: state.nodes,
          edges: state.edges
        };
      }
    }),
    {
      name: 'orchestration-store'
    }
  )
);
