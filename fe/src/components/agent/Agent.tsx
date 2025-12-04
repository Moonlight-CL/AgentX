import React, { useEffect, useState } from 'react';
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
  Tooltip,
  message,
} from 'antd';
import type { FormInstance } from 'antd/es/form';
import { 
  PlusOutlined, 
  EyeOutlined, 
  EditOutlined, 
  DeleteOutlined,
  ShareAltOutlined
} from '@ant-design/icons';
import { AGENT_TYPES, TOOL_TYPES } from '../../services/api';
import type { Agent, Tool } from '../../services/api';
import { useAgentStore } from '../../store/agentStore';
import { useModelProviders, type ModelConfig } from '../../hooks/useModelProviders';
import { useUserStore } from '../../store/userStore';

const { Title } = Typography;
const { TextArea } = Input;
const { Option } = Select;

export const AgentManager: React.FC = () => {
  // Form instances - initialized with default values
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const [shareForm] = Form.useForm();
  
  // Share modal state
  const [shareModalVisible, setShareModalVisible] = useState(false);
  const [users, setUsers] = useState<any[]>([]);
  const [userGroups, setUserGroups] = useState<any[]>([]);
  const [shareLoading, setShareLoading] = useState(false);
  
  // Get model providers from configuration
  const { 
    providers, 
    getProviderNumber, 
    getProviderKey,
    getModelIds,
  } = useModelProviders();
  
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
    setSelectedAgent,
    createAgent,
    updateAgent,
    deleteAgent,
    handleToolClick,
    handleViewAgent,
    handleEditAgent,
    handleDeleteAgent
  } = useAgentStore();
  
  // Get current user from user store
  const { user } = useUserStore();
  
  // Helper function to check if current user can edit/delete/share an agent
  const canManageAgent = (agent: Agent): boolean => {
    if (!user) return false;
    // User can manage agent if they are the creator or user is administrator
    return agent.creator === user.user_id || user.is_admin === true;
  };
  
  // Reset form when modal is opened and set initial values
  useEffect(() => {
    if (createModalVisible && providers.length > 0) {
      createForm.resetFields();
      // Set initial values after providers are loaded
      createForm.setFieldsValue({
        agent_type: AGENT_TYPES.PLAIN,
        model_provider: getProviderNumber(providers[0].key),
        model_id: providers[0].models.length > 0 ? providers[0].models[0].config.model_id : 'Custom',
        tools: [],
      });
    }
  }, [createModalVisible, createForm, providers]);
  
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

  // Helper Function: Extract model extras from model config
  const extractModelExtras = (model: ModelConfig) => {
    return {
      ...(model.config.api_base_url && { base_url: model.config.api_base_url }),
      ...(model.config.api_key && { api_key: model.config.api_key }),
      ...(model.config.max_tokens && { max_tokens: model.config.max_tokens }),
      ...(model.config.temperature && { temperature: model.config.temperature }),
      ...(model.config.top_p && { top_p: model.config.top_p }),
    };
  };
  // Handle form values change
  const handleFormValuesChange = (changedValues: { model_provider?: number, model_id?: string }, form: FormInstance) => {
    if ('model_provider' in changedValues) {
      // Reset model_id when model_provider changes
      const providerKey = getProviderKey(changedValues.model_provider!);
      const modelIds = getModelIds(providerKey);
      const provider = providers.find(p => p.key === providerKey)!;

      if (modelIds.length > 0) {
        form.setFieldsValue({ model_id: modelIds[0] });
        const model = provider.models.find(m => m.config.model_id === modelIds[0])!;
        form.setFieldsValue({ extras: extractModelExtras(model) });
      } else {
        form.setFieldsValue({ model_id: 'Custom' });
      }
    }

    if ('model_id' in changedValues) {
      const provider = getProviderKey(form.getFieldValue("model_provider"))!;
      const modelId = changedValues.model_id!;
      const model = providers.find(p => p.key === provider)!.models.find(m => m.config.model_id === modelId)!;

      form.setFieldsValue({ extras: extractModelExtras(model) });
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
    const providerKey = getProviderKey(provider);
    const providerInfo = providers.find(p => p.key === providerKey);
    return providerInfo?.displayName || providerKey || '未知';
  };

  // Handle share agent
  const handleShareAgent = async (agent: Agent) => {
    try {
      // Set selected agent for sharing
      setSelectedAgent(agent);
      
      // Load users and user groups for sharing
      setShareLoading(true);
      
      // Fetch users and user groups
      const [usersResponse, groupsResponse] = await Promise.all([
        fetch('/api/user/list', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('user-storage') ? JSON.parse(localStorage.getItem('user-storage')!).state?.token : ''}`,
          },
        }),
        fetch('/api/user/groups/list', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('user-storage') ? JSON.parse(localStorage.getItem('user-storage')!).state?.token : ''}`,
          },
        })
      ]);
      
      if (usersResponse.ok) {
        const usersData = await usersResponse.json();
        setUsers(usersData);
      }
      
      if (groupsResponse.ok) {
        const groupsData = await groupsResponse.json();
        if (groupsData.success) {
          setUserGroups(groupsData.data);
        }
      }
      
      // Set current sharing values
      shareForm.setFieldsValue({
        shared_users: agent.shared_users || [],
        shared_groups: agent.shared_groups || [],
        is_public: agent.is_public || false
      });
      
      setShareModalVisible(true);
    } catch (error) {
      message.error('Failed to load sharing data');
      console.error('Error loading sharing data:', error);
    } finally {
      setShareLoading(false);
    }
  };

  // Handle share form submission
  const handleShareSubmit = async (values: any) => {
    if (!selectedAgent) return;
    
    try {
      setShareLoading(true);
      
      const response = await fetch(`/api/agent/${selectedAgent.id}/share`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('user-storage') ? JSON.parse(localStorage.getItem('user-storage')!).state?.token : ''}`,
        },
        body: JSON.stringify({
          shared_users: values.shared_users || [],
          shared_groups: values.shared_groups || [],
          is_public: values.is_public || false
        })
      });
      
      if (response.ok) {
        message.success('Agent shared successfully');
        setShareModalVisible(false);
        shareForm.resetFields();
        fetchAgents(); // Refresh agents list
      } else {
        const errorData = await response.json();
        message.error(errorData.detail || 'Failed to share agent');
      }
    } catch (error) {
      message.error('Failed to share agent');
      console.error('Error sharing agent:', error);
    } finally {
      setShareLoading(false);
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
      render: (_: unknown, record: Agent) => {
        const canManage = canManageAgent(record);
        
        return (
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
              styles={{ root: { maxWidth: '400px' } }}
            >
              <Button 
                type="text" 
                icon={<EyeOutlined />} 
                onClick={() => handleViewAgent(record)} 
              />
            </Tooltip>
            
            {canManage && (
              <Tooltip title="编辑">
                <Button 
                  type="text" 
                  icon={<EditOutlined />} 
                  onClick={() => handleEditAgent(record)} 
                />
              </Tooltip>
            )}
            
            {canManage && (
              <Tooltip title="分享">
                <Button 
                  type="text" 
                  icon={<ShareAltOutlined />} 
                  onClick={() => handleShareAgent(record)} 
                />
              </Tooltip>
            )}
            
            {canManage && (
              <Tooltip title="删除">
                <Button 
                  type="text" 
                  danger 
                  icon={<DeleteOutlined />} 
                  onClick={() => handleDeleteAgent(record)} 
                />
              </Tooltip>
            )}
          </Space>
        );
      },
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
        model_provider: providers.length > 0 ? getProviderNumber(providers[0].key) : 1,
        model_id: providers.length > 0 && providers[0].models.length > 0 ? providers[0].models[0].config.model_id : 'Custom',
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
          {providers.map((provider) => (
            <Option key={provider.key} value={getProviderNumber(provider.key)}>
              {provider.key}
            </Option>
          ))}
        </Select>
      </Form.Item>
      
      <Form.Item
        noStyle
        shouldUpdate={(prevValues, currentValues) => prevValues.model_provider !== currentValues.model_provider}
      >
        {({ getFieldValue }) => {
          const providerNumber = getFieldValue('model_provider');
          const providerKey = getProviderKey(providerNumber);
          const provider = providers.find(p => p.key === providerKey);
          
          return (
            <Form.Item
              name="model_id"
              label="Model ID"
              rules={[{ required: true, message: '请选择Model ID' }]}
            >
              <Select>
                {provider && provider.models.length > 0 ? (
                  provider.models.map((model, index) => (
                    <Option key={index} value={model.config.model_id}>
                      {model.config.model_id}
                    </Option>
                  ))
                ) : (
                  <Option value="Custom">Custom Model</Option>
                )}
              </Select>
            </Form.Item>
          );
        }}
      </Form.Item>

      <Form.Item
        noStyle
        shouldUpdate={(prevValues, currentValues) => prevValues.model_id !== currentValues.model_id}
      >
        {
          ({ getFieldValue }) => {
            const providerNumber = getFieldValue('model_provider');
            const providerKey = getProviderKey(providerNumber);
            const provider = providers.find(p => p.key === providerKey);

            const model_id = getFieldValue('model_id');
            const model = provider?.models.find(m => m.config.model_id === model_id);
            
            const extra_items = buildAgentExtrasFields(model);
            return <>{extra_items}</>;
          }
        }
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
        {getProviderKey(selectedAgent.model_provider) === 'openai' && selectedAgent.extras && (
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
                {providers.map((provider) => (
                  <Option key={provider.key} value={getProviderNumber(provider.key)}>
                    {provider.key}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            
            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) => prevValues.model_provider !== currentValues.model_provider}
            >
              {({ getFieldValue }) => {
                const providerNumber = getFieldValue('model_provider');
                const providerKey = getProviderKey(providerNumber);
                const provider = providers.find(p => p.key === providerKey);
                
                return (
                  <Form.Item
                    name="model_id"
                    label="Model ID"
                    rules={[{ required: true, message: '请选择Model ID' }]}
                  >
                    <Select>
                      {provider && provider.models.length > 0 ? (
                        provider.models.map((model, index) => (
                          <Option key={index} value={model.config.model_id}>
                            {model.config.model_id}
                          </Option>
                        ))
                      ) : (
                        <Option value="Custom">Custom Model</Option>
                      )}
                    </Select>
                  </Form.Item>
                );
              }}
            </Form.Item>

            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) => prevValues.model_id !== currentValues.model_id}
            >
              {
                ({ getFieldValue }) => {
                  const providerNumber = getFieldValue('model_provider');
                  const providerKey = getProviderKey(providerNumber);
                  const provider = providers.find(p => p.key === providerKey);

                  const model_id = getFieldValue('model_id');
                  const model = provider?.models.find(m => m.config.model_id === model_id);
                  let extra_items = buildAgentExtrasFields(model);
                  return <>{extra_items}</>;
                }
              }
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

        {/* Share Agent Modal */}
        <Modal
          title={`分享 Agent: ${selectedAgent?.display_name || selectedAgent?.name}`}
          open={shareModalVisible}
          onCancel={() => {
            setShareModalVisible(false);
            shareForm.resetFields();
          }}
          onOk={() => shareForm.submit()}
          width={600}
          okText="保存"
          cancelText="取消"
          confirmLoading={shareLoading}
        >
          <Form
            form={shareForm}
            layout="vertical"
            onFinish={handleShareSubmit}
            onValuesChange={(changedValues) => {
              // When is_public changes to true, clear shared_users and shared_groups
              if (changedValues.is_public === true) {
                shareForm.setFieldsValue({
                  shared_users: [],
                  shared_groups: []
                });
              }
            }}
          >
            <Form.Item
              name="is_public"
              label="公开访问"
              valuePropName="checked"
            >
              <Select>
                <Option value={true}>是 - 所有用户都可以使用</Option>
                <Option value={false}>否 - 仅分享给指定用户/组</Option>
              </Select>
            </Form.Item>
            
            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) => prevValues.is_public !== currentValues.is_public}
            >
              {({ getFieldValue }) => {
                const isPublic = getFieldValue('is_public');
                return (
                  <>
                    <Form.Item
                      name="shared_users"
                      label="分享给用户"
                      help="选择要分享给的特定用户"
                    >
                      <Select
                        mode="multiple"
                        placeholder="选择用户"
                        allowClear
                        loading={shareLoading}
                        disabled={isPublic}
                      >
                        {users.map(user => (
                          <Option key={user.user_id} value={user.user_id}>
                            {user.username} ({user.email || 'No email'})
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>
                    
                    <Form.Item
                      name="shared_groups"
                      label="分享给用户组"
                      help="选择要分享给的用户组"
                    >
                      <Select
                        mode="multiple"
                        placeholder="选择用户组"
                        allowClear
                        loading={shareLoading}
                        disabled={isPublic}
                      >
                        {userGroups.map(group => (
                          <Option key={group.id} value={group.id}>
                            {group.name} - {group.description}
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>
                  </>
                );
              }}
            </Form.Item>
          </Form>
        </Modal>

      </Card>
    </div>
  );
};
function buildAgentExtrasFields(model: ModelConfig | undefined) {
  let extra_items = [];
  if (model?.config.api_base_url) {
    extra_items.push(
      <Form.Item
        key={`${Date.now()}-${Math.floor(Math.random() * 100)}`}
        hidden
        name={['extras', 'base_url']}
        label="Base URL">
        <Input />
      </Form.Item>
    );
  }
  if (model?.config.api_key) {
    extra_items.push(
      <Form.Item
        key={`${Date.now()}-${Math.floor(Math.random() * 100)}`}
        hidden
        name={['extras', 'api_key']}
        label="API KEY">
        <Input />
      </Form.Item>
    );
  }
  if (model?.config.max_tokens) {
    extra_items.push(
      <Form.Item
        key={`${Date.now()}-${Math.floor(Math.random() * 100)}`}
        hidden
        name={['extras', 'max_tokens']}
        label="Max Tokens">
        <Input type="number" />
      </Form.Item>
    );
  }
  if (model?.config.temperature) {
    extra_items.push(
      <Form.Item
        key={`${Date.now()}-${Math.floor(Math.random() * 100)}`}
        hidden
        name={['extras', 'temperature']}
        label="Temperature">
        <Input type="number" step="0.1" />
      </Form.Item>
    );
  }
  if (model?.config.top_p) {
    extra_items.push(
      <Form.Item
        key={`${Date.now()}-${Math.floor(Math.random() * 100)}`}
        hidden
        name={['extras', 'top_p']}
        label="Top P">
        <Input type="number" step="0.1" />
      </Form.Item>
    );
  }
  return extra_items;
}

