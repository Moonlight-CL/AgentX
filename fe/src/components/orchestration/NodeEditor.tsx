import React, { useEffect, useState } from 'react';
import { Form, Input, Select, Button, Space, Divider, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useOrchestrationStore } from '../../store/orchestrationStore';
import { useAgentStore } from '../../store/agentStore';
import { AGENT_TYPES, agentAPI } from '../../services/api';
import type { Agent } from '../../services/api';
import type { Node } from '@xyflow/react';
import { useModelProviders } from '../../hooks/useModelProviders';

const { TextArea } = Input;
const { Option } = Select;

interface NodeEditorProps {
  inline?: boolean;
  nodes?: Node[];
  onUpdateNodeData?: (nodeId: string, dataUpdates: Partial<any>) => void;
}

export const NodeEditor: React.FC<NodeEditorProps> = ({ inline = false, nodes = [], onUpdateNodeData }) => {
  const [form] = Form.useForm();
  const { agents, availableTools, fetchAgents, fetchTools } = useAgentStore();
  const [isNewAgent, setIsNewAgent] = useState(false);
  const [selectedAgentData, setSelectedAgentData] = useState<Agent | null>(null);
  
  // Get model providers from configuration
  const { 
    providers, 
    getProviderNumber, 
    getProviderKey,
    getModelIds,
    getModelConfig
  } = useModelProviders();
  
  const {
    selectedNode,
    setSelectedNode,
    updateNode
  } = useOrchestrationStore();

  // Initialize agents and tools data
  useEffect(() => {
    if (agents.length === 0) {
      fetchAgents();
    }
    if (availableTools.length === 0) {
      fetchTools();
    }
  }, [agents.length, availableTools.length, fetchAgents, fetchTools]);

  // Get current node data from ReactFlow nodes
  const getCurrentNodeData = () => {
    if (!selectedNode) return null;
    
    const node = nodes.find(n => n.id === selectedNode);
    if (!node) return null;

    return {
      id: node.id,
      name: node.id,
      displayName: node.data.label || 'Node',
      description: '',
      type: node.data.nodeType || 'agent',
      agentId: node.data.agentId || '',
      agentData: node.data.agentData || null,
      isNew: node.data.isNew || false,
      config: node.data.config || {}
    };
  };

  useEffect(() => {
    if (selectedNode) {

      const nodeData = getCurrentNodeData();
      if (!nodeData) return;

      // 如果节点有 agentId，查找对应的 Agent 并填充表单
      if (nodeData.agentId && agents.length > 0) {
        const agent = agents.find(a => a.id === nodeData.agentId);
        if (agent) {
          setIsNewAgent(false);
          setSelectedAgentData(agent);
          
          // 填充表单数据
          form.setFieldsValue({
            agentId: agent.id,
            name: agent.name,
            display_name: agent.display_name,
            description: agent.description,
            agent_type: agent.agent_type,
            model_provider: agent.model_provider,
            model_id: agent.model_id,
            sys_prompt: agent.sys_prompt,
            tools: agent.tools.map((tool: any) => tool.name),
            envs: agent.envs,
            extras: agent.extras || {}
          });
        }
      } else {
        // 节点没有 agentId 或为空，设置为新建 Agent 状态
        setIsNewAgent(true);
        setSelectedAgentData(null);
        
        // 重置表单为新建Agent的默认值
        const firstProvider = providers.length > 0 ? providers[0] : null;
        const firstModel = firstProvider && firstProvider.models.length > 0 ? firstProvider.models[0] : null;
        console.log(firstModel);
        
        form.setFieldsValue({
          name: '',
          display_name: '',
          description: '',
          agent_type: AGENT_TYPES.PLAIN,
          model_provider: firstProvider ? getProviderNumber(firstProvider.key) : 1,
          model_id: firstModel ? firstModel.config.model_id : 'Custom',
          sys_prompt: '',
          tools: [],
          envs: '',
          extras: {}
        });
      }
    }
  }, [selectedNode, agents, nodes]);

  const handleFormValuesChange = (changedValues: { model_provider?: number, model_id?: string }) => {
    if ('model_provider' in changedValues) {
      // Reset model_id when model_provider changes
      const providerKey = getProviderKey(changedValues.model_provider!);
      const modelIds = getModelIds(providerKey);
      const provider = providers.find(p => p.key === providerKey)!;
      
      if (modelIds.length > 0) {
        form.setFieldsValue({ model_id: modelIds[0] });
        const model = provider.models.find(m => m.config.model_id === modelIds[0])!;
        if(model.config.api_base_url && model.config.api_key) {
            form.setFieldsValue({extras: { base_url: model.config.api_base_url, api_key: model.config.api_key }});
        }else {
          form.setFieldsValue({ extras: {} });
        }
      } else {
        form.setFieldsValue({ model_id: 'Custom' });
      }
    }
    
    // Handle model_id changes to update extras with model config
    if ('model_id' in changedValues) {
      const currentProvider = form.getFieldValue('model_provider');
      const providerKey = getProviderKey(currentProvider);
      const modelConfig = getModelConfig(providerKey, changedValues.model_id!);
      
      if (modelConfig) {
        // Extract all config except model_id and merge with existing extras
        const { model_id, ...modelExtras } = modelConfig.config;
        const currentExtras = form.getFieldValue('extras') || {};
        
        form.setFieldsValue({ 
          extras: { 
            ...currentExtras, 
            ...modelExtras 
          } 
        });
      }
    }
  };

  const handleSave = async (values: any) => {
    if (!selectedNode) return;

    try {
      if (isNewAgent) {
        // 新建 Agent 时，调用 API 创建 Agent
        const agentData = {
          name: values.name,
          display_name: values.display_name,
          description: values.description,
          agent_type: values.agent_type,
          model_provider: values.model_provider,
          model_id: values.model_id,
          sys_prompt: values.sys_prompt,
          tools: values.tools || [],
          envs: values.envs || '',
          extras: values.extras || {}
        };

        // 调用 API 创建 Agent
        const createdAgent = await agentAPI.createOrUpdateAgent(agentData);
        
        // 更新节点数据，存储新创建的 Agent ID
        if (onUpdateNodeData) {
          onUpdateNodeData(selectedNode, {
            label: createdAgent.display_name,
            agentId: createdAgent.id,
            isNew: false,
            agentData: createdAgent
          });
        }

        // 更新本地状态
        setIsNewAgent(false);
        setSelectedAgentData(createdAgent);
        
        // 刷新 agents 列表以包含新创建的 agent
        fetchAgents();
        
        // 更新表单以显示创建的 Agent ID
        form.setFieldsValue({
          agentId: createdAgent.id,
          ...values
        });

        message.success('Agent 创建成功！');
        console.log('Agent created successfully:', createdAgent);
      } else {
        // 使用已有 Agent，只更新节点数据
        updateNode(selectedNode, values);
        message.success('节点配置已保存！');
      }

      if (!inline) {
        setSelectedNode(null);
      }
    } catch (error) {
      console.error('Error saving agent:', error);
      message.error('保存失败：' + (error instanceof Error ? error.message : '未知错误'));
    }
  };

  const handleCancel = () => {
    setSelectedNode(null);
    form.resetFields();
  };

  if (!selectedNode) {
    return (
      <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
        请选择一个节点进行编辑
      </div>
    );
  }

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleSave}
      size="small"
      onValuesChange={handleFormValuesChange}
    >
      {/* Agent Selection Dropdown - Always show for Agent nodes */}
      <Form.Item
        label="选择操作"
        help="选择新建Agent或使用已有Agent"
      >
        <Select 
          placeholder="选择新建或已有Agent" 
          value={isNewAgent ? 'new_agent' : selectedAgentData?.id}
          size='large'
          onChange={(value) => {

            if (value === 'new_agent') {
              setIsNewAgent(true);
              setSelectedAgentData(null);
              
              // 更新节点数据，清除 agentId 并更新标签
              if (selectedNode && onUpdateNodeData) {
                onUpdateNodeData(selectedNode, {
                  label: 'New Agent',
                  agentId: '',
                  isNew: true,
                  agentData: null
                });
              }
              
              // 重置表单为新建Agent的默认值
              const firstProvider = providers.length > 0 ? providers[0] : null;
              const firstModel = firstProvider && firstProvider.models.length > 0 ? firstProvider.models[0] : null;
              
              form.setFieldsValue({
                name: '',
                display_name: '',
                description: '',
                agent_type: AGENT_TYPES.PLAIN,
                model_provider: firstProvider ? getProviderNumber(firstProvider.key) : 1,
                model_id: firstModel ? firstModel.config.model_id : 'Custom',
                sys_prompt: '',
                tools: [],
                envs: '',
                extras: {}
              });
            } else {
              // 选择已有Agent
              const agent = agents.find(a => a.id === value);
              if (agent) {
                setIsNewAgent(false);
                setSelectedAgentData(agent);
                
                // 更新节点数据，存储 agentId 并更新标签
                if (selectedNode && onUpdateNodeData) {
                  onUpdateNodeData(selectedNode, {
                    label: agent.display_name,
                    agentId: agent.id,
                    isNew: false,
                    agentData: agent
                  });
                }
                
                // 填充表单数据
                form.setFieldsValue({
                  agentId: agent.id,
                  name: agent.name,
                  display_name: agent.display_name,
                  description: agent.description,
                  agent_type: agent.agent_type,
                  model_provider: agent.model_provider,
                  model_id: agent.model_id,
                  sys_prompt: agent.sys_prompt,
                  tools: agent.tools.map((tool: any) => tool.name),
                  envs: agent.envs,
                  extras: agent.extras || {}
                });
              }
            }
          }}
        >
          <Option value="new_agent" label="新建Agent">
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <PlusOutlined style={{ marginRight: '8px', color: '#1890ff' }} />
              <span>新建Agent</span>
            </div>
          </Option>
          {agents.map(agent => (
            <Option key={agent.id} value={agent.id} label={agent.display_name}>
              <div style={{ display: 'block' }}>
                <div style={{ fontWeight: 500, lineHeight: '1.2' }}>{agent.display_name}</div>
                <div style={{ 
                  fontSize: '11px', 
                  color: '#999',
                  lineHeight: '1.2',
                  marginTop: '2px',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  maxWidth: '250px'
                }}>
                  {agent.description}
                </div>
              </div>
            </Option>
          ))}
        </Select>
      </Form.Item>

      <Divider style={{ margin: '12px 0' }} />

      {isNewAgent ? (
        // New Agent Form - based on Agent.tsx
        <>
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
            <Input 
              placeholder="例如: 计算器" />
          </Form.Item>
          
          <Form.Item
            name="description"
            label="描述"
            rules={[{ required: true, message: '请输入描述' }]}
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
                  {provider.displayName}
                </Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) => prevValues.model_provider !== currentValues.model_provider || prevValues.model_id !== currentValues.model_id}
          >
            {({ getFieldValue }) => {
              const providerNumber = getFieldValue('model_provider');
              const providerKey = getProviderKey(providerNumber);
              const provider = providers.find(p => p.key === providerKey);
              console.log("provider", provider);
              
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
                            )
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
                            )
                          }
                          return <>{extra_items}</>;
                        }
            }
          </Form.Item>
          
          <Form.Item
            name="sys_prompt"
            label="System Prompt"
            rules={[{ required: true, message: '请输入System Prompt' }]}
          >
            <TextArea rows={3} placeholder="输入Agent的System Prompt" />
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
                    <div>{tool.display_name || tool.name}</div>
                    <div style={{ fontSize: '11px', color: '#999' }}>{tool.desc}</div>
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
            <TextArea rows={2} placeholder="例如: AWS_REGION=us-west-2" />
          </Form.Item>
        </>
      ) : (
        // Existing Agent - Show form fields with agent data populated
        <>
          <Form.Item
            name="name"
            label="Agent名称"
          >
            <Input disabled />
          </Form.Item>
          
          <Form.Item
            name="display_name"
            label="显示名称"
          >
            <Input disabled />
          </Form.Item>
          
          <Form.Item
            name="description"
            label="描述"
          >
            <TextArea rows={2} disabled />
          </Form.Item>
          
          <Form.Item
            name="agent_type"
            label="Agent类型"
          >
            <Select disabled>
              <Option value={AGENT_TYPES.PLAIN}>Plain</Option>
              <Option value={AGENT_TYPES.ORCHESTRATOR}>Orchestrator</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name="model_provider"
            label="Model Provider"
          >
            <Select disabled>
              {providers.map((provider) => (
                <Option key={provider.key} value={getProviderNumber(provider.key)}>
                  {provider.displayName}
                </Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item
            name="model_id"
            label="Model ID"
          >
            <Input disabled />
          </Form.Item>
          
          {selectedAgentData && getProviderKey(selectedAgentData.model_provider) === 'openai' && (
            <>
              <Form.Item
                name={['extras', 'base_url']}
                label="Base URL"
              >
                <Input disabled />
              </Form.Item>
              
              <Form.Item
                name={['extras', 'api_key']}
                label="API Key"
              >
                <Input.Password disabled />
              </Form.Item>
            </>
          )}
          
          <Form.Item
            name="sys_prompt"
            label="System Prompt"
          >
            <TextArea rows={3} disabled />
          </Form.Item>
          
          <Form.Item
            name="tools"
            label="Tools"
          >
            <Select
              mode="multiple"
              disabled
              optionLabelProp="label"
            >
              {availableTools.map((tool, index) => (
                <Option key={index} value={tool.name} label={tool.name}>
                  <div>
                    <div>{tool.display_name || tool.name}</div>
                    <div style={{ fontSize: '11px', color: '#999' }}>{tool.desc}</div>
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
            <TextArea rows={2} disabled />
          </Form.Item>
        </>
      )}

      <Divider style={{ margin: '12px 0' }} />

      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
        <Button size="small" onClick={handleCancel}>
          取消
        </Button>
        <Button size="small" type="primary" htmlType="submit">
          保存
        </Button>
      </Space>
    </Form>
  );
};
