import React, { useCallback, useEffect, useState } from 'react';
import { 
  ReactFlow, 
  addEdge, 
  useNodesState, 
  useEdgesState, 
  Controls, 
  MiniMap, 
  Background,
  ConnectionMode,
  Panel,
  Handle,
  Position
} from '@xyflow/react';
import type { Node, Edge, Connection } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { 
  Card, 
  Form, 
  Input, 
  Select, 
  Button, 
  Space, 
  Divider, 
  Row, 
  Col,
  InputNumber,
  message,
  Typography,
  Modal,
} from 'antd';
import { SaveOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { useOrchestrationStore } from '../../store/orchestrationStore';
import { NodePalette } from './NodePalette';
import { NodeEditor } from './NodeEditor';
import type { 
  OrchestrationConfig, 
  OrchestrationType, 
  AgentNode, 
  OrchestrationNode,
  ReactFlowNodeData,
} from '../../types/orchestration';

const { TextArea } = Input;
const { Option } = Select;
const { Title } = Typography;

// Custom node types with handles for connections
const createNodeTypes = (orchestrationType: OrchestrationType) => ({
  agentNode: ({ data }: { data: ReactFlowNodeData }) => (
    <div style={{
      padding: '10px',
      border: '2px solid #1890ff',
      borderRadius: '8px',
      background: 'white',
      minWidth: '120px',
      textAlign: 'center',
      position: 'relative'
    }}>
      {/* Input handle (target) - only show for graph, workflow, agent_as_tool */}
      {(orchestrationType === 'graph' || orchestrationType === 'workflow' || orchestrationType === 'agents_as_tools') && (
        <Handle
          type="target"
          position={orchestrationType === 'workflow' ? Position.Left : Position.Top}
          style={{
            background: '#1890ff',
            width: '8px',
            height: '8px',
            border: '2px solid white'
          }}
        />
      )}
      
      <div style={{ fontWeight: 'bold', color: '#1890ff' }}>Agent</div>
      <div style={{ fontSize: '12px', marginTop: '4px' }}>{data.label}</div>
      
      {/* Output handle (source) - only show for graph, workflow, agent_as_tool */}
      {(orchestrationType === 'graph' || orchestrationType === 'workflow' || orchestrationType === 'agents_as_tools') && (
        <Handle
          type="source"
          position={Position.Bottom}
          style={{
            background: '#1890ff',
            width: '8px',
            height: '8px',
            border: '2px solid white'
          }}
        />
      )}
    </div>
  ),
  orchestrationNode: ({ data }: { data: ReactFlowNodeData }) => (
    <div style={{
      padding: '10px',
      border: '2px solid #52c41a',
      borderRadius: '8px',
      background: 'white',
      minWidth: '120px',
      textAlign: 'center',
      position: 'relative'
    }}>
      {/* Input handle (target) - only show for graph, workflow, agent_as_tool */}
      {(orchestrationType === 'graph' || orchestrationType === 'workflow' || orchestrationType === 'agents_as_tools') && (
        <Handle
          type="target"
          position={Position.Top}
          style={{
            background: '#52c41a',
            width: '8px',
            height: '8px',
            border: '2px solid white'
          }}
        />
      )}
      
      <div style={{ fontWeight: 'bold', color: '#52c41a' }}>Orchestration</div>
      <div style={{ fontSize: '12px', marginTop: '4px' }}>{data.label}</div>
      
      {/* Output handle (source) - only show for graph, workflow, agent_as_tool */}
      {(orchestrationType === 'graph' || orchestrationType === 'workflow' || orchestrationType === 'agents_as_tools') && (
        <Handle
          type="source"
          position={Position.Bottom}
          style={{
            background: '#52c41a',
            width: '8px',
            height: '8px',
            border: '2px solid white'
          }}
        />
      )}
    </div>
  ),
});

export const OrchestrationEditor: React.FC = () => {
  const [form] = Form.useForm();
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [orchestrationType, setOrchestrationType] = useState<OrchestrationType>('swarm');
  const [showTypeChangeModal, setShowTypeChangeModal] = useState(false);
  const [pendingOrchestationType, setPendingOrchestationType] = useState<OrchestrationType | null>(null);
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEditMode = Boolean(id);
  
  const {
    currentOrchestration,
    orchestrations,
    selectedNode,
    createOrchestration,
    updateOrchestration,
    setNodeEditorVisible,
    setSelectedNode,
    setCurrentOrchestration,
  } = useOrchestrationStore();

  // Load orchestration data when in edit mode
  useEffect(() => {
    if (isEditMode && id) {
      const orchestration = orchestrations.find(o => o.id === id);
      if (orchestration) {
        setCurrentOrchestration(orchestration);
      }
    }
  }, [isEditMode, id, orchestrations, setCurrentOrchestration]);

  // Initialize form and editor when orchestration changes
  useEffect(() => {
    if (currentOrchestration) {
      // Load existing orchestration
      setOrchestrationType(currentOrchestration.type as OrchestrationType);
      form.setFieldsValue({
        name: currentOrchestration.name,
        displayName: currentOrchestration.displayName,
        description: currentOrchestration.description,
        type: currentOrchestration.type,
        entryPoint: currentOrchestration.entryPoint,
        maxHandoffs: currentOrchestration.maxHandoffs,
        maxIterations: currentOrchestration.maxIterations,
        executionTimeout: currentOrchestration.executionTimeout,
        nodeTimeout: currentOrchestration.nodeTimeout,
      });

      // Convert orchestration nodes to ReactFlow nodes
      const reactFlowNodes: Node[] = currentOrchestration.nodes.map(node => ({
        id: node.id,
        type: node.type === 'agent' ? 'agentNode' : 'orchestrationNode',
        position: node.position,
        data: {
          label: node.displayName,
          nodeType: node.type,
          agentId: node.type === 'agent' ? (node as AgentNode).agentId : undefined,
          orchestrationId: node.type === 'orchestration' ? (node as OrchestrationNode).orchestrationId : undefined,
          config: node.type === 'agent' ? (node as AgentNode).agentConfig : (node as OrchestrationNode).orchestrationConfig,
        }
      }));

      // Convert orchestration edges to ReactFlow edges
      const reactFlowEdges: Edge[] = currentOrchestration.edges.map(edge => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: 'default',
        sourceHandle: null,
        targetHandle: null,
        label: edge.label || '',
        data: { condition: edge.condition }
      }));

      setNodes(reactFlowNodes);
      setEdges(reactFlowEdges);
    } else {
      // Reset for new orchestration
      setOrchestrationType('swarm');
      form.resetFields();
      setNodes([]);
      setEdges([]);
    }
  }, [currentOrchestration, form, setNodes, setEdges]);

  const onConnect = useCallback(
    (params: Connection) => {
      const newEdge = {
        ...params,
        id: `edge-${Date.now()}`,
        type: 'default',
      };
      setEdges((eds) => addEdge(
        { ...newEdge, type: newEdge.type ?? 'default' },
        eds.map(e => ({ ...e, type: e.type ?? 'default' }))
      ));
    },
    [setEdges]
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      setSelectedNode(node.id);
      setNodeEditorVisible(true);
    },
    [setSelectedNode, setNodeEditorVisible]
  );

  // Handle keyboard events for deleting nodes
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Delete' && selectedNode) {
        // Delete selected node
        setNodes((nds) => nds.filter(node => node.id !== selectedNode));
        setEdges((eds) => eds.filter(edge => edge.source !== selectedNode && edge.target !== selectedNode));
        setSelectedNode(null);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [selectedNode, setNodes, setEdges, setSelectedNode]);

  // const handleDeleteNode = useCallback((nodeId: string) => {
  //   setNodes((nds) => nds.filter(node => node.id !== nodeId));
  //   setEdges((eds) => eds.filter(edge => edge.source !== nodeId && edge.target !== nodeId));
  //   if (selectedNode === nodeId) {
  //     setSelectedNode(null);
  //   }
  // }, [setNodes, setEdges, selectedNode, setSelectedNode]);

  const handleSave = async (values: any) => {
    try {
      // Convert ReactFlow nodes back to orchestration nodes
      const orchestrationNodes: (AgentNode | OrchestrationNode)[] = nodes.map(node => {
        const baseNode = {
          id: node.id,
          name: node.id,
          displayName: node.data.label as string,
          description: '',
          position: node.position,
        };

        if (node.data.nodeType === 'agent') {
          return {
            ...baseNode,
            type: 'agent' as const,
            agentId: node.data.agentId as string | undefined,
            agentConfig: node.data.config as any,
          };
        } else {
          return {
            ...baseNode,
            type: 'orchestration' as const,
            orchestrationId: node.data.orchestrationId as string | undefined,
            orchestrationConfig: node.data.config as any,
          };
        }
      });

      // Convert ReactFlow edges back to orchestration edges
      const orchestrationEdges = edges.map(edge => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        condition: edge.data?.condition,
        label: (edge.label as string) || '',
      }));

      const orchestrationConfig: Partial<OrchestrationConfig> = {
        ...values,
        type: orchestrationType, // Ensure type is included
        nodes: orchestrationNodes,
        edges: orchestrationEdges,
      };

      if (currentOrchestration) {
        await updateOrchestration(currentOrchestration.id, orchestrationConfig);
        message.success('编排更新成功');
      } else {
        await createOrchestration(orchestrationConfig);
        message.success('编排创建成功');
      }
      
      // Navigate back to orchestration list
      navigate('/orchestration');
    } catch (error) {
      message.error('保存失败');
      console.error('Save error:', error);
    }
  };

  const handleAddNode = (nodeData: { type: 'agent' | 'orchestration'; label: string; config?: any }) => {
    const newNode: Node = {
      id: `node-${Date.now()}`,
      type: nodeData.type === 'agent' ? 'agentNode' : 'orchestrationNode',
      position: { x: Math.random() * 400, y: Math.random() * 400 },
      data: {
        label: nodeData.label,
        nodeType: nodeData.type,
        agentId: nodeData.config?.agentId,
        agentData: nodeData.config?.agentData,
        isNew: nodeData.config?.isNew,
        config: nodeData.config,
      }
    };
    setNodes((nds) => [...nds, newNode]);
    
    // 自动选中新创建的节点
    setSelectedNode(newNode.id);
    setNodeEditorVisible(true);
  };

  const handleUpdateNodeData = useCallback((nodeId: string, dataUpdates: Partial<ReactFlowNodeData>) => {
    setNodes((nds) => 
      nds.map(node => 
        node.id === nodeId 
          ? { 
              ...node, 
              data: { 
                ...node.data, 
                ...dataUpdates
              } 
            }
          : node
      )
    );
  }, [setNodes]);

  const handleOrchestrationTypeChange = (newType: OrchestrationType) => {
    if (nodes.length > 0 || edges.length > 0) {
      // Show confirmation dialog if there are existing nodes or edges
      setPendingOrchestationType(newType);
      setShowTypeChangeModal(true);
    } else {
      // Directly change type if no nodes/edges exist
      setOrchestrationType(newType);
      form.setFieldsValue({ type: newType });
    }
  };

  const handleConfirmTypeChange = () => {
    if (pendingOrchestationType) {
      setOrchestrationType(pendingOrchestationType);
      form.setFieldsValue({ type: pendingOrchestationType });
      // Clear nodes and edges
      setNodes([]);
      setEdges([]);
      setSelectedNode(null);
      // Reset form fields that are type-specific
      form.setFieldsValue({
        entryPoint: undefined,
        orchestratorAgent: undefined,
        parallelExecution: false,
      });
    }
    setShowTypeChangeModal(false);
    setPendingOrchestationType(null);
  };

  const handleCancelTypeChange = () => {
    setShowTypeChangeModal(false);
    setPendingOrchestationType(null);
  };

  const handleBack = () => {
    navigate('/orchestration');
  };

  return (
    <div style={{ padding: '24px', height: 'calc(100vh - 48px)' }}>
      {/* Header with back button */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        marginBottom: '24px',
        borderBottom: '1px solid #f0f0f0',
        paddingBottom: '16px'
      }}>
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={handleBack}
          style={{ marginRight: '16px' }}
        >
          返回
        </Button>
        <Title level={2} style={{ margin: 0 }}>
          {isEditMode ? '编辑编排' : '新建编排'}
        </Title>
      </div>

      <div style={{ height: 'calc(100% - 80px)', display: 'flex', position: 'relative' }}>
        {/* Left Panel - Orchestration Type & Node Palette */}
        <div style={{ width: '280px', padding: '16px', borderRight: '1px solid #f0f0f0' }}>
          {/* Orchestration Type Selection */}
          <Card title="编排类型" size="small" style={{ marginBottom: '16px' }}>
            <Select 
              placeholder="选择编排类型"
              value={orchestrationType}
              onChange={handleOrchestrationTypeChange}
              style={{ width: '100%' }}
            >
              <Option value="swarm">Swarm (群体协作)</Option>
              <Option value="graph">Graph (有向图)</Option>
              <Option value="workflow">Workflow (工作流)</Option>
              <Option value="agents_as_tools">Agent as Tool (智能体工具)</Option>
            </Select>
          </Card>

          {/* Node Palette */}
          <NodePalette onAddNode={handleAddNode} />
        </div>

        {/* Center Panel - Visual Editor */}
        <div style={{ flex: 1, position: 'relative' }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={() => setSelectedNode(null)} // Clear selection when clicking canvas
            nodeTypes={createNodeTypes(orchestrationType)}
            connectionMode={ConnectionMode.Loose}
            fitView
          >
            <Controls />
            <MiniMap />
            <Background />
            <Panel position="top-left">
              <div style={{ background: 'white', padding: '8px', borderRadius: '4px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
                节点数: {nodes.length} | 连接数: {edges.length}
              </div>
            </Panel>
          </ReactFlow>
        </div>

        {/* Right Panel - Floating Property Panel */}
        <div style={{
          position: 'absolute',
          top: '16px',
          right: '16px',
          width: '400px', // 320px * 1.2 = 384px (加宽20%)
          maxHeight: 'calc(100% - 32px)',
          zIndex: 1000
        }}>
          {selectedNode ? (
            // Show selected node properties
            <Card 
              title="新建或选择Agent" 
              size="default"
              style={{ 
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                border: '1px solid #d9d9d9',
                display: 'flex',
                flexDirection: 'column',
                height: '100%',
              }}
              styles={{
                body: { flex: 1, overflowY: 'auto', padding: '16px' }
              }}
            >
              <NodeEditor nodes={nodes} onUpdateNodeData={handleUpdateNodeData} />
            </Card>
          ) : (
            // Show orchestration properties when no node is selected
            <Card 
              title="编排设置" 
              size="default"
              style={{ 
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                border: '1px solid #d9d9d9',
                display: 'flex',
                flexDirection: 'column',
                height: '100%'
              }}
              styles={{
                body: { flex: 1, overflowY: 'auto', padding: '16px' }
              }}
            >
              <Form
                form={form}
                layout="vertical"
                onFinish={handleSave}
                initialValues={{
                  type: 'swarm',
                  maxHandoffs: 20,
                  maxIterations: 20,
                  executionTimeout: 900,
                  nodeTimeout: 300,
                  repetitiveHandoffDetectionWindow: 0,
                  repetitiveHandoffMinUniqueAgents: 0,
                  maxNodeExecutions: 5,
                  resetOnRevisit: false,
                }}
              >
                <Form.Item
                  name="name"
                  label="编排名称"
                  rules={[
                    { required: true, message: '请输入编排名称' },
                    { pattern: /^[a-zA-Z0-9_]+$/, message: '只能包含英文字母、数字和下划线' },
                  ]}
                >
                  <Input placeholder="例如: my_swarm" />
                </Form.Item>

                <Form.Item
                  name="displayName"
                  label="显示名称"
                  rules={[{ required: true, message: '请输入显示名称' }]}
                >
                  <Input placeholder="例如: 我的智能体群" />
                </Form.Item>

                <Form.Item
                  name="description"
                  label="描述"
                  rules={[{ required: true, message: '请输入描述' }]}
                >
                  <TextArea rows={3} placeholder="描述编排的功能和用途" />
                </Form.Item>

                <Divider />

                {/* Type-specific properties */}
                {orchestrationType === 'swarm' && (
                  <>
                    <Form.Item name="entryPoint" label="入口点" rules={[{ required: true, message: '请选择入口点' }]}>
                      <Select placeholder="选择入口智能体">
                        {nodes.filter(node => node.data.nodeType === 'agent').map(node => (
                          <Option key={node.id} value={node.data.agentId}>
                            {node.data.label as string}
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item name="maxHandoffs" label="最大交接次数">
                          <InputNumber min={1} max={100} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="maxIterations" label="最大迭代次数">
                          <InputNumber min={1} max={100} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item name="executionTimeout" label="执行超时(秒)">
                          <InputNumber min={60} max={3600} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="nodeTimeout" label="节点超时(秒)">
                          <InputNumber min={30} max={1800} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item name="repetitiveHandoffDetectionWindow" label="重复交接检测窗口">
                          <InputNumber min={0} max={20} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="repetitiveHandoffMinUniqueAgents" label="最少唯一智能体数">
                          <InputNumber min={0} max={10} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                    </Row>
                  </>
                )}
              
                {orchestrationType === 'graph' && (
                  <>
                    <Form.Item name="entryPoint" label="入口点" rules={[{ required: true, message: '请选择入口点' }]}>
                      <Select placeholder="选择入口节点">
                        {nodes.map(node => (
                          <Option key={node.id} value={node.data.agentId}>
                            {node.data.label as string}
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item name="maxNodeExecutions" label="最大节点执行次数">
                          <InputNumber min={1} max={100} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="executionTimeout" label="执行超时(秒)">
                          <InputNumber min={60} max={3600} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item name="nodeTimeout" label="节点超时(秒)">
                          <InputNumber min={30} max={1800} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="resetOnRevisit" label="再访问重制" valuePropName="checked">
                          <Select>
                            <Option value={true}>是</Option>
                            <Option value={false}>否</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                    </Row>
                  </>
                )}

                {/*
                {orchestrationType === 'workflow' && (
                  <>
                    <Form.Item name="entryPoint" label="入口点" rules={[{ required: true, message: '请选择入口点' }]}>
                      <Select placeholder="选择入口节点">
                        {nodes.map(node => (
                          <Option key={node.id} value={node.id}>
                            {node.data.label as string}
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item name="maxIterations" label="最大迭代次数">
                          <InputNumber min={1} max={100} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="executionTimeout" label="执行超时(秒)">
                          <InputNumber min={60} max={3600} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Form.Item name="parallelExecution" label="并行执行" valuePropName="checked">
                      <Select defaultValue={false}>
                        <Option value={true}>启用</Option>
                        <Option value={false}>禁用</Option>
                      </Select>
                    </Form.Item>
                  </>
                )}
                */}
                {orchestrationType === 'agents_as_tools' && (
                  <>
                    <Form.Item name="orchestratorAgent" label="编排器智能体" rules={[{ required: true, message: '请选择编排器智能体' }]}>
                      <Select placeholder="选择编排器智能体">
                        {nodes.filter(node => node.data.nodeType === 'agent').map(node => (
                          <Option key={node.id} value={node.data.agentId}>
                            {node.data.label as string}
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>
                  </>
                )} 

                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Button type="primary" htmlType="submit" icon={<SaveOutlined />}>
                    保存
                  </Button>
                  {/* <Button icon={<PlayCircleOutlined />}>
                    测试运行
                  </Button> */}
                </Space>
              </Form>
            </Card>
          )}
        </div>
      </div>

      {/* Orchestration Type Change Confirmation Modal */}
      <Modal
        title="确认更改编排类型"
        open={showTypeChangeModal}
        onOk={handleConfirmTypeChange}
        onCancel={handleCancelTypeChange}
        okText="确认"
        cancelText="取消"
      >
        <p>更改编排类型将清除当前所有节点和连接。</p>
        <p>您确定要继续吗？</p>
      </Modal>
    </div>
  );
};
