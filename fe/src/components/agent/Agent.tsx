import React, { useEffect } from 'react';
import { 
  Card, 
  Typography, 
  Table, 
  Button, 
  Space, 
  Modal, 
  Form, 
  Input, 
  Select, 
  Tooltip
} from 'antd';
import type { FormInstance } from 'antd/es/form';
import { 
  PlusOutlined, 
  EyeOutlined, 
  EditOutlined, 
  DeleteOutlined
} from '@ant-design/icons';
import { AGENT_TYPES, MODEL_PROVIDERS, BEDROCK_MODELS, TOOL_TYPES, OPENAI_MODELS } from '../../services/api';
import type { Agent, Tool } from '../../services/api';
import { useAgentStore } from '../../store/agentStore';

const { Title } = Typography;
const { TextArea } = Input;
const { Option } = Select;

export const AgentManager: React.FC = () => {
  // Form instances - initialized with default values
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  
  // Get state and actions from Zustand store
  const { 
    agents, 
    availableTools, 
    loading, 
    createModalVisible, 
    editModalVisible,
    toolDetailModalVisible, 
    agentDetailModalVisible, 
    deleteModalVisible,
    selectedTool, 
    selectedAgent,  
    fetchAgents,
    fetchTools,
    setCreateModalVisible,
    setEditModalVisible,
    setToolDetailModalVisible,
    setAgentDetailModalVisible,
    setDeleteModalVisible,
    createAgent,
    updateAgent,
    deleteAgent,
    handleToolClick,
    handleViewAgent,
    handleEditAgent,
    handleDeleteAgent
  } = useAgentStore();
  
  // Reset form when modal is opened
  useEffect(() => {
    if (createModalVisible) {
      createForm.resetFields();
    }
  }, [createModalVisible, createForm]);
  
  // Initialize edit form when selected agent changes
  useEffect(() => {
    if (selectedAgent && editModalVisible) {
      // Convert tool objects to tool names for the form
      const toolNames = selectedAgent.tools.map(tool => tool.name);
      
      // Set form values
      editForm.setFieldsValue({
        ...selectedAgent,
        tools: toolNames,
        extras: selectedAgent.extras || {}
      });
    }
  }, [selectedAgent, editModalVisible, editForm]);
  
  // Handle form values change
  const handleFormValuesChange = (changedValues: { model_provider?: number }, form: FormInstance) => {
    if ('model_provider' in changedValues) {
      // Reset model_id when model_provider changes
      if (changedValues.model_provider === MODEL_PROVIDERS.BEDROCK) {
        form.setFieldsValue({ model_id: BEDROCK_MODELS[0], extras: {} });
      } else if (changedValues.model_provider === MODEL_PROVIDERS.OPENAI) {
        form.setFieldsValue({ model_id: OPENAI_MODELS[0], extras: { base_url: '', api_key: '' } });
      } else {
        form.setFieldsValue({ model_id: 'custom', extras: {} });
      }
    }
  };
  
  // Load data on component mount
  useEffect(() => {
    fetchAgents();
    fetchTools();
  }, [fetchAgents, fetchTools]);
  
  // Handle create agent form submission
  const handleCreateAgent = async (values: Omit<Agent, 'id'> & { tools: string[] }) => {
    // Convert tool names to complete Tool objects
    const toolObjects: Tool[] = [];
    
    // Find the complete Tool object for each tool name
    for (const toolName of values.tools) {
      const foundTool = availableTools.find(tool => tool.name === toolName);
      if (foundTool) {
        toolObjects.push(foundTool);
      }
    }
    
    // Create a new agent object with complete Tool objects
    const agentWithTools: Omit<Agent, 'id'> = {
      ...values,
      tools: toolObjects
    };
    
    await createAgent(agentWithTools);
    createForm.resetFields();
  };
  
  // Handle edit agent form submission
  const handleUpdateAgent = async (values: Agent & { tools: string[] }) => {
    // Convert tool names to complete Tool objects
    const toolObjects: Tool[] = [];
    
    // Find the complete Tool object for each tool name
    for (const toolName of values.tools) {
      const foundTool = availableTools.find(tool => tool.name === toolName);
      if (foundTool) {
        toolObjects.push(foundTool);
      }
    }
    
    // Create an updated agent object with complete Tool objects
    const updatedAgent: Agent = {
      ...values,
      tools: toolObjects
    };
    
    await updateAgent(updatedAgent);
    editForm.resetFields();
  };
  
  // Helper function to get agent type name
  const getAgentTypeName = (type: number): string => {
    switch (type) {
      case AGENT_TYPES.PLAIN:
        return 'Plain';
      case AGENT_TYPES.ORCHESTRATOR:
        return 'Orchestrator';
      default:
        return '未知';
    }
  };

  // Helper function to get model provider name
  const getModelProviderName = (provider: number): string => {
    switch (provider) {
      case MODEL_PROVIDERS.BEDROCK:
        return 'Bedrock';
      case MODEL_PROVIDERS.OPENAI:
        return 'OpenAI';
      case MODEL_PROVIDERS.ANTHROPIC:
        return 'Anthropic';
      case MODEL_PROVIDERS.LITELLM:
        return 'LiteLLM';
      case MODEL_PROVIDERS.OLLAMA:
        return 'Ollama';
      case MODEL_PROVIDERS.CUSTOM:
        return 'Custom';
      default:
        return '未知';
    }
  };


  // Table columns
  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      width: 120,
      resizable: true,
    },
    {
      title: 'Display Name',
      dataIndex: 'display_name',
      key: 'display_name',
      width: 150,
      resizable: true,
    },
    {
      title: 'Agent类型',
      dataIndex: 'agent_type',
      key: 'agent_type',
      width: 120,
      resizable: true,
      render: (type: number) => getAgentTypeName(type),
    },
    {
      title: '模型提供商',
      dataIndex: 'model_provider',
      key: 'model_provider',
      width: 120,
      resizable: true,
      render: (provider: number) => getModelProviderName(provider),
    },
    {
      title: '模型ID',
      dataIndex: 'model_id',
      key: 'model_id',
      width: 150,
      resizable: true,
      ellipsis: true,
      render: (modelId: string) => (
        <Tooltip title={modelId}>
          <span>{modelId}</span>
        </Tooltip>
      ),
    },
    {
      title: 'Tools',
      dataIndex: 'tools',
      key: 'tools',
      width: 150,
      resizable: true,
      render: (tools: Tool[]) => (
        <Space direction="vertical">
          {tools.map((tool, index) => (
            <a key={index} onClick={() => handleToolClick(tool)}>
              {tool.display_name? tool.display_name: tool.name}
            </a>
          ))}
          <span style={{ color: '#999' }}>{tools.length} 个工具</span>
        </Space>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      fixed: 'right' as const,
      width: 120,
      render: (_: unknown, record: Agent) => (
        <Space>
          <Tooltip 
            title={
              <div>
                <p><strong>System Prompt:</strong></p>
                <div style={{ maxWidth: '300px', maxHeight: '200px', overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                  {record.sys_prompt}
                </div>
              </div>
            }
            placement="left"
            overlayStyle={{ maxWidth: '400px' }}
          >
            <Button 
              type="text" 
              icon={<EyeOutlined />} 
              onClick={() => handleViewAgent(record)} 
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button 
              type="text" 
              icon={<EditOutlined />} 
              onClick={() => handleEditAgent(record)} 
            />
          </Tooltip>
          <Tooltip title="删除">
            <Button 
              type="text" 
              danger 
              icon={<DeleteOutlined />} 
              onClick={() => handleDeleteAgent(record)} 
            />
          </Tooltip>
        </Space>
      ),
    },
  ];
  
  // Create agent form
  const createAgentForm = (
    <Form
      form={createForm}
      layout="vertical"
      onFinish={handleCreateAgent}
      onValuesChange={(changedValues) => handleFormValuesChange(changedValues, createForm)}
      initialValues={{
        agent_type: AGENT_TYPES.PLAIN,
        model_provider: MODEL_PROVIDERS.BEDROCK,
        model_id: BEDROCK_MODELS[0],
        tools: [],
      }}
    >
      <Form.Item
        name="name"
        label="Agent名称"
        rules={[
          { required: true, message: '请输入Agent名称' },
          { max: 100, message: '名称不能超过100个字符' },
          { pattern: /^[a-zA-Z0-9_]+$/, message: '只能包含英文字母、数字和下划线' },
        ]}
      >
        <Input placeholder="例如: calculator" />
      </Form.Item>
      
      <Form.Item
        name="display_name"
        label="显示名称"
        rules={[
          { required: true, message: '请输入显示名称' },
          { max: 100, message: '显示名称不能超过100个字符' },
        ]}
      >
        <Input placeholder="例如: 计算器" />
      </Form.Item>
      
      <Form.Item
        name="description"
        label="描述"
        rules={[
          { required: true, message: '请输入描述' },
        ]}
      >
        <TextArea rows={2} placeholder="描述Agent的功能和能力" />
      </Form.Item>
      
      <Form.Item
        name="agent_type"
        label="Agent类型"
        rules={[{ required: true, message: '请选择Agent类型' }]}
      >
        <Select>
          <Option value={AGENT_TYPES.PLAIN}>Plain</Option>
          <Option value={AGENT_TYPES.ORCHESTRATOR}>Orchestrator</Option>
        </Select>
      </Form.Item>
      
      <Form.Item
        name="model_provider"
        label="Model Provider"
        rules={[{ required: true, message: '请选择Model Provider' }]}
      >
        <Select>
          <Option value={MODEL_PROVIDERS.BEDROCK}>Bedrock</Option>
          <Option value={MODEL_PROVIDERS.OPENAI}>OpenAI</Option>
          <Option value={MODEL_PROVIDERS.ANTHROPIC}>Anthropic</Option>
          <Option value={MODEL_PROVIDERS.LITELLM}>LiteLLM</Option>
          <Option value={MODEL_PROVIDERS.OLLAMA}>Ollama</Option>
          <Option value={MODEL_PROVIDERS.CUSTOM}>Custom</Option>
        </Select>
      </Form.Item>
      
      <Form.Item
        noStyle
        shouldUpdate={(prevValues, currentValues) => prevValues.model_provider !== currentValues.model_provider}
      >
        {({ getFieldValue }) => (
          <Form.Item
            name="model_id"
            label="Model ID"
            rules={[{ required: true, message: '请选择Model ID' }]}
          >
            <Select>
              {getFieldValue('model_provider') === MODEL_PROVIDERS.BEDROCK ? (
                BEDROCK_MODELS.map((model, index) => (
                  <Option key={index} value={model}>{model}</Option>
                ))
              ) : getFieldValue('model_provider') === MODEL_PROVIDERS.OPENAI ? (
                OPENAI_MODELS.map((model, index) => (
                  <Option key={index} value={model}>{model}</Option>
                ))
              ) : (
                <Option value="custom">Custom Model</Option>
              )}
            </Select>
          </Form.Item>
        )}
      </Form.Item>
      
      <Form.Item
        noStyle
        shouldUpdate={(prevValues, currentValues) => prevValues.model_provider !== currentValues.model_provider}
      >
        {({ getFieldValue }) => (
          getFieldValue('model_provider') === MODEL_PROVIDERS.OPENAI && (
            <>
              <Form.Item
                name={['extras', 'base_url']}
                label="Base URL"
                rules={[{ required: true, message: '请输入Base URL' }]}
              >
                <Input placeholder="例如: https://api.openai.com/v1" />
              </Form.Item>
              
              <Form.Item
                name={['extras', 'api_key']}
                label="API Key"
                rules={[{ required: true, message: '请输入API Key' }]}
              >
                <Input.Password placeholder="请输入API Key" />
              </Form.Item>
            </>
          )
        )}
      </Form.Item>
      
      <Form.Item
        name="sys_prompt"
        label="System Prompt"
        rules={[{ required: true, message: '请输入System Prompt' }]}
      >
        <TextArea rows={5} placeholder="输入Agent的System Prompt" />
      </Form.Item>
      
      <Form.Item
        name="tools"
        label="Tools"
      >
        <Select
          mode="multiple"
          placeholder="选择Tools"
          optionLabelProp="label"
        >
          {availableTools.map((tool, index) => (
            <Option key={index} value={tool.name} label={tool.name}>
              <div>
                <div>{tool.display_name? tool.display_name: tool.name}</div>
                <div style={{ fontSize: '12px', color: '#999' }}>{tool.desc}</div>
              </div>
            </Option>
          ))}
        </Select>
      </Form.Item>
      
      <Form.Item
        name="envs"
        label="环境变量"
        help="每行一个环境变量，格式为 key=value"
      >
        <TextArea rows={3} placeholder="例如: AWS_REGION=us-west-2" />
      </Form.Item>
    </Form>
  );
  
  // Tool detail modal content
  const toolDetailContent = selectedTool && (
    <div>
      <p><strong>名称:</strong> {selectedTool.name}</p>
      <p><strong>类别:</strong> {selectedTool.category}</p>
      <p><strong>描述:</strong> {selectedTool.desc}</p>
      <p>
        <strong>类型:</strong> {
          selectedTool.type === TOOL_TYPES.STRANDS ? 'Strands' :
          selectedTool.type === TOOL_TYPES.MCP ? 'MCP' :
          selectedTool.type === TOOL_TYPES.AGENT ? 'Agent' :
          selectedTool.type === TOOL_TYPES.PYTHON ? 'Python' : '未知'
        }
      </p>
      {selectedTool.type === TOOL_TYPES.MCP && selectedTool.mcp_server_url && (
        <p><strong>MCP Server URL:</strong> {selectedTool.mcp_server_url}</p>
      )}
      {selectedTool.type === TOOL_TYPES.AGENT && selectedTool.agent_id && (
        <p><strong>Agent ID:</strong> {selectedTool.agent_id}</p>
      )}
    </div>
  );
  
  // Agent detail modal content
  const agentDetailContent = selectedAgent && (
    <div style={{ maxHeight: '70vh', overflow: 'auto' }}>
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ borderBottom: '1px solid #f0f0f0', paddingBottom: '10px' }}>基本信息</h3>
        <p><strong>ID:</strong> {selectedAgent.id}</p>
        <p><strong>名称:</strong> {selectedAgent.name}</p>
        <p><strong>显示名称:</strong> {selectedAgent.display_name}</p>
        <p><strong>描述:</strong> {selectedAgent.description}</p>
        <p><strong>Agent类型:</strong> {getAgentTypeName(selectedAgent.agent_type)}</p>
      </div>
      
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ borderBottom: '1px solid #f0f0f0', paddingBottom: '10px' }}>模型信息</h3>
        <p><strong>模型提供商:</strong> {getModelProviderName(selectedAgent.model_provider)}</p>
        <p><strong>模型ID:</strong> {selectedAgent.model_id}</p>
        {selectedAgent.model_provider === MODEL_PROVIDERS.OPENAI && selectedAgent.extras && (
          <>
            <p><strong>Base URL:</strong> {selectedAgent.extras.base_url}</p>
            <p><strong>API Key:</strong> {'*'.repeat(10)}</p>
          </>
        )}
      </div>
      
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ borderBottom: '1px solid #f0f0f0', paddingBottom: '10px' }}>System Prompt</h3>
        <div style={{ 
          background: '#f5f5f5', 
          padding: '10px', 
          borderRadius: '4px',
          whiteSpace: 'pre-wrap',
          fontFamily: 'monospace'
        }}>
          {selectedAgent.sys_prompt}
        </div>
      </div>
      
      {selectedAgent.envs && (
        <div style={{ marginBottom: '20px' }}>
          <h3 style={{ borderBottom: '1px solid #f0f0f0', paddingBottom: '10px' }}>环境变量</h3>
          <div style={{ 
            background: '#f5f5f5', 
            padding: '10px', 
            borderRadius: '4px',
            whiteSpace: 'pre-wrap',
            fontFamily: 'monospace'
          }}>
            {selectedAgent.envs}
          </div>
        </div>
      )}
      
      <div>
        <h3 style={{ borderBottom: '1px solid #f0f0f0', paddingBottom: '10px' }}>工具列表 ({selectedAgent.tools.length})</h3>
        {selectedAgent.tools.length > 0 ? (
          <ul style={{ paddingLeft: '20px' }}>
            {selectedAgent.tools.map((tool, index) => (
              <li key={index} style={{ marginBottom: '10px' }}>
                <div><strong>{tool.name}</strong> - {tool.desc}</div>
                <div style={{ fontSize: '12px', color: '#999' }}>
                  类别: {tool.category} | 
                  类型: {
                    tool.type === TOOL_TYPES.STRANDS ? 'Strands' :
                    tool.type === TOOL_TYPES.MCP ? 'MCP' :
                    tool.type === TOOL_TYPES.AGENT ? 'Agent' :
                    tool.type === TOOL_TYPES.PYTHON ? 'Python' : '未知'
                  }
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p>该Agent没有配置工具</p>
        )}
      </div>
    </div>
  );
  
  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <Title level={2}>Strands Agent 管理</Title>
          <Button 
            type="primary" 
            icon={<PlusOutlined />} 
            onClick={() => setCreateModalVisible(true)}
          >
            新增
          </Button>
        </div>
        
        <Table 
          columns={columns} 
          dataSource={agents} 
          rowKey="id" 
          loading={loading}
          scroll={{ x: 1500 }}
          pagination={{
            defaultPageSize: 10,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50'],
            showTotal: (total) => `共 ${total} 条记录`
          }}
        />
        
        {/* Create Agent Modal */}
        <Modal
          title="新增 Strands Agent"
          open={createModalVisible}
          onCancel={() => setCreateModalVisible(false)}
          onOk={() => createForm.submit()}
          width={700}
          okText="创建"
          cancelText="取消"
        >
          {createAgentForm}
        </Modal>
        
        {/* Edit Agent Modal */}
        <Modal
          title="编辑 Strands Agent"
          open={editModalVisible}
          onCancel={() => setEditModalVisible(false)}
          onOk={() => editForm.submit()}
          width={700}
          okText="保存"
          cancelText="取消"
        >
          <Form
            form={editForm}
            layout="vertical"
            onFinish={handleUpdateAgent}
            onValuesChange={(changedValues) => handleFormValuesChange(changedValues, editForm)}
          >
            <Form.Item name="id" hidden>
              <Input />
            </Form.Item>
            
            <Form.Item
              name="name"
              label="Agent名称"
              rules={[
                { required: true, message: '请输入Agent名称' },
                { max: 100, message: '名称不能超过100个字符' },
                { pattern: /^[a-zA-Z0-9_]+$/, message: '只能包含英文字母、数字和下划线' },
              ]}
            >
              <Input placeholder="例如: calculator" />
            </Form.Item>
            
            <Form.Item
              name="display_name"
              label="显示名称"
              rules={[
                { required: true, message: '请输入显示名称' },
                { max: 100, message: '显示名称不能超过100个字符' },
              ]}
            >
              <Input placeholder="例如: 计算器" />
            </Form.Item>
            
            <Form.Item
              name="description"
              label="描述"
              rules={[
                { required: true, message: '请输入描述' },
              ]}
            >
              <TextArea rows={4} placeholder="描述Agent的功能和能力" />
            </Form.Item>
            
            <Form.Item
              name="agent_type"
              label="Agent类型"
              rules={[{ required: true, message: '请选择Agent类型' }]}
            >
              <Select>
                <Option value={AGENT_TYPES.PLAIN}>Plain</Option>
                <Option value={AGENT_TYPES.ORCHESTRATOR}>Orchestrator</Option>
              </Select>
            </Form.Item>
            
            <Form.Item
              name="model_provider"
              label="Model Provider"
              rules={[{ required: true, message: '请选择Model Provider' }]}
            >
              <Select>
                <Option value={MODEL_PROVIDERS.BEDROCK}>Bedrock</Option>
                <Option value={MODEL_PROVIDERS.OPENAI}>OpenAI</Option>
                <Option value={MODEL_PROVIDERS.ANTHROPIC}>Anthropic</Option>
                <Option value={MODEL_PROVIDERS.LITELLM}>LiteLLM</Option>
                <Option value={MODEL_PROVIDERS.OLLAMA}>Ollama</Option>
                <Option value={MODEL_PROVIDERS.CUSTOM}>Custom</Option>
              </Select>
            </Form.Item>
            
            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) => prevValues.model_provider !== currentValues.model_provider}
            >
              {({ getFieldValue }) => (
                <Form.Item
                  name="model_id"
                  label="Model ID"
                  rules={[{ required: true, message: '请选择Model ID' }]}
                >
                  <Select>
                    {getFieldValue('model_provider') === MODEL_PROVIDERS.BEDROCK ? (
                      BEDROCK_MODELS.map((model, index) => (
                        <Option key={index} value={model}>{model}</Option>
                      ))
                    ) : getFieldValue('model_provider') === MODEL_PROVIDERS.OPENAI ? (
                      OPENAI_MODELS.map((model, index) => (
                        <Option key={index} value={model}>{model}</Option>
                      ))
                    ) : (
                      <Option value="custom">Custom Model</Option>
                    )}
                  </Select>
                </Form.Item>
              )}
            </Form.Item>
            
            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) => prevValues.model_provider !== currentValues.model_provider}
            >
              {({ getFieldValue }) => (
                getFieldValue('model_provider') === MODEL_PROVIDERS.OPENAI && (
                  <>
                    <Form.Item
                      name={['extras', 'base_url']}
                      label="Base URL"
                      rules={[{ required: true, message: '请输入Base URL' }]}
                    >
                      <Input placeholder="例如: https://api.openai.com/v1" />
                    </Form.Item>
                    
                    <Form.Item
                      name={['extras', 'api_key']}
                      label="API Key"
                      rules={[{ required: true, message: '请输入API Key' }]}
                    >
                      <Input.Password placeholder="请输入API Key" />
                    </Form.Item>
                  </>
                )
              )}
            </Form.Item>
            
            <Form.Item
              name="sys_prompt"
              label="System Prompt"
              rules={[{ required: true, message: '请输入System Prompt' }]}
            >
              <TextArea rows={6} placeholder="输入Agent的System Prompt" />
            </Form.Item>
            
            <Form.Item
              name="tools"
              label="Tools"
            >
              <Select
                mode="multiple"
                placeholder="选择Tools"
                optionLabelProp="label"
              >
                {availableTools.map((tool, index) => (
                  <Option key={index} value={tool.name} label={tool.name}>
                    <div>
                      <div>{tool.name}</div>
                      <div style={{ fontSize: '12px', color: '#999' }}>{tool.desc}</div>
                    </div>
                  </Option>
                ))}
              </Select>
            </Form.Item>
            
            <Form.Item
              name="envs"
              label="环境变量"
              help="每行一个环境变量，格式为 key=value"
            >
              <TextArea rows={4} placeholder="例如: AWS_REGION=us-west-2" />
            </Form.Item>
          </Form>
        </Modal>
        
        {/* Tool Detail Modal */}
        <Modal
          title="Tool 详情"
          open={toolDetailModalVisible}
          onCancel={() => setToolDetailModalVisible(false)}
          footer={[
            <Button key="close" onClick={() => setToolDetailModalVisible(false)}>
              关闭
            </Button>
          ]}
        >
          {toolDetailContent}
        </Modal>
        
        {/* Agent Detail Modal */}
        <Modal
          title="Agent 详情"
          open={agentDetailModalVisible}
          onCancel={() => setAgentDetailModalVisible(false)}
          width={800}
          footer={[
            <Button key="close" onClick={() => setAgentDetailModalVisible(false)}>
              关闭
            </Button>
          ]}
        >
          {agentDetailContent}
        </Modal>

        <Modal
          title="确认删除"
          open={deleteModalVisible}
          onCancel={() => setDeleteModalVisible(false)}
          onOk={() => {
            if (selectedAgent) {
              console.log('Deleting agent:', selectedAgent.id);
              deleteAgent(selectedAgent.id);
            }
          }}
          okText="确认"
          cancelText="取消"
        >
          <p>确定要删除这个 { "[" + selectedAgent?.name + "]"} Agent 吗？</p>
          <p>请注意，删除后无法恢复，请谨慎操作。</p>
        </Modal>

      </Card>
    </div>
  );
};
