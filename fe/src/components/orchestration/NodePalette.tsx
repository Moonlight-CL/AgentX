import React, { useState, useEffect } from 'react';
import { Card, Button, Divider, Modal, Select } from 'antd';
import { UserOutlined, ApartmentOutlined, PlusOutlined } from '@ant-design/icons';
import { useAgentStore } from '../../store/agentStore';

const { Option } = Select;

interface NodePaletteProps {
  onAddNode: (nodeData: { type: 'agent' | 'orchestration'; label: string; config?: any }) => void;
}

export const NodePalette: React.FC<NodePaletteProps> = ({ onAddNode }) => {
  const { agents, fetchAgents } = useAgentStore();
  const [agentModalVisible, setAgentModalVisible] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState<string | undefined>();

  // Initialize agents data
  useEffect(() => {
    if (agents.length === 0) {
      fetchAgents();
    }
  }, [agents.length, fetchAgents]);

  const handleAddAgentNode = () => {
    // 直接在画布中创建Agent节点，默认为新建状态
    onAddNode({
      type: 'agent',
      label: 'New Agent',
      config: { isNew: true }
    });
  };

  const handleAgentModalOk = () => {
    if (selectedAgentId && selectedAgentId !== 'new_agent') {
      const agent = agents.find(a => a.id === selectedAgentId);
      onAddNode({
        type: 'agent',
        label: agent?.display_name || 'Agent',
        config: { agentId: selectedAgentId, agentData: agent }
      });
    } else {
      // 新建智能体
      onAddNode({
        type: 'agent',
        label: 'New Agent',
        config: { isNew: true }
      });
    }
    setAgentModalVisible(false);
    setSelectedAgentId(undefined);
  };

  const handleAgentModalCancel = () => {
    setAgentModalVisible(false);
    setSelectedAgentId(undefined);
  };

  const handleAddOrchestrationNode = () => {
    onAddNode({
      type: 'orchestration',
      label: 'Orchestration',
      config: {}
    });
  };

  return (
    <>
      <Card title="节点面板" size="small">
        <div style={{ marginBottom: '12px' }}>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>智能体节点</div>
          <Button
            block
            size="small"
            icon={<UserOutlined />}
            onClick={handleAddAgentNode}
          >
            智能体
          </Button>
        </div>

        <Divider style={{ margin: '12px 0' }} />

        <div>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>编排节点</div>
          <Button
            block
            size="small"
            icon={<ApartmentOutlined />}
            onClick={handleAddOrchestrationNode}
          >
            嵌套编排
          </Button>
        </div>

        <Divider style={{ margin: '12px 0' }} />

        <div style={{ fontSize: '11px', color: '#999', lineHeight: '1.4' }}>
          <div>操作提示：</div>
          <div>• 点击按钮添加节点</div>
          <div>• 拖拽节点调整位置</div>
          <div>• 连接节点创建流程</div>
          <div>• 点击节点编辑配置</div>
          <div>• 按Delete键删除选中节点</div>
        </div>
      </Card>

      {/* Agent Selection Modal */}
      <Modal
        title="选择智能体"
        open={agentModalVisible}
        onOk={handleAgentModalOk}
        onCancel={handleAgentModalCancel}
        okText="确定"
        cancelText="取消"
        width={500}
      >
        <div style={{ marginBottom: '16px' }}>
          <div style={{ marginBottom: '8px' }}>请选择要添加的智能体：</div>
          <Select
            placeholder="选择现有智能体或新建"
            size ="large"
            value={selectedAgentId}
            onChange={setSelectedAgentId}
            style={{ width: '100%' }}
            allowClear
          >
            <Option value="new_agent" label="新建智能体">
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <PlusOutlined style={{ marginRight: '8px', color: '#1890ff' }} />
                <span>新建智能体</span>
              </div>
            </Option>
            {agents.map(agent => (
              <Option key={agent.id} value={agent.id} label={agent.display_name}>
                <div style={{ display: 'block' }}>
                  <div style={{ fontWeight: 500, lineHeight: '1.0' }}>{agent.display_name}</div>
                  <div style={{ 
                    fontSize: '12px', 
                    color: '#999', 
                    lineHeight: '1.2',
                    marginTop: '4px',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    maxWidth: '400px'
                  }}>
                    {agent.description}
                  </div>
                </div>
              </Option>
            ))}
          </Select>
        </div>
        
        {selectedAgentId && selectedAgentId !== 'new_agent' ? (
          <div style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px' }}>
            <div style={{ fontSize: '12px', color: '#666' }}>
              将添加现有智能体到编排中，可以在节点属性中进一步配置。
            </div>
          </div>
        ) : (
          <div style={{ background: '#e6f7ff', padding: '12px', borderRadius: '4px' }}>
            <div style={{ fontSize: '12px', color: '#1890ff' }}>
              将创建新的智能体节点，您可以在节点属性中配置智能体的详细信息。
            </div>
          </div>
        )}
      </Modal>
    </>
  );
};
