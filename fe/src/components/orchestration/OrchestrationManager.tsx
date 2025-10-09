import React, { useEffect } from 'react';
import { 
  Card, 
  Typography, 
  Table, 
  Button, 
  Space, 
  Modal, 
  Tag,
  Tooltip,
  Dropdown
} from 'antd';
import type { MenuProps } from 'antd';
import { 
  PlusOutlined, 
  EyeOutlined, 
  EditOutlined, 
  DeleteOutlined,
  PlayCircleOutlined,
  MoreOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useOrchestrationStore } from '../../store/orchestrationStore';
import { OrchestrationExecution } from './OrchestrationExecution';
import type { OrchestrationConfig, OrchestrationType } from '../../types/orchestration';

const { Title } = Typography;

export const OrchestrationManager: React.FC = () => {
  const navigate = useNavigate();
  const {
    orchestrations,
    loading,
    executionModalVisible,
    fetchOrchestrations,
    setExecutionModalVisible,
    setCurrentOrchestration,
    deleteOrchestration,
  } = useOrchestrationStore();

  useEffect(() => {
    fetchOrchestrations();
  }, [fetchOrchestrations]);

  const handleCreateNew = () => {
    setCurrentOrchestration(null);
    navigate('/orchestration/create');
  };

  const handleEdit = (orchestration: OrchestrationConfig) => {
    setCurrentOrchestration(orchestration);
    navigate(`/orchestration/edit/${orchestration.id}`);
  };

  const handleView = (orchestration: OrchestrationConfig) => {
    setCurrentOrchestration(orchestration);
    // Could open a read-only view modal
  };

  const handleExecute = (orchestration: OrchestrationConfig) => {
    setCurrentOrchestration(orchestration);
    setExecutionModalVisible(true);
  };

  const handleDelete = (orchestration: OrchestrationConfig) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除编排 "${orchestration.displayName}" 吗？此操作无法撤销。`,
      okText: '确认',
      cancelText: '取消',
      onOk: () => deleteOrchestration(orchestration.id),
    });
  };

  const getOrchestrationTypeTag = (type: OrchestrationType) => {
    const typeConfig = {
      swarm: { color: 'blue', text: 'Swarm' },
      graph: { color: 'green', text: 'Graph' },
      workflow: { color: 'orange', text: 'Workflow' },
      agents_as_tools: { color: 'purple', text: 'Agent as Tool' }
    };
    
    const config = typeConfig[type] || { color: 'default', text: type };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const getActionMenuItems = (orchestration: OrchestrationConfig): MenuProps['items'] => [
    {
      key: 'view',
      icon: <EyeOutlined />,
      label: '查看详情',
      onClick: () => handleView(orchestration),
    },
    {
      key: 'edit',
      icon: <EditOutlined />,
      label: '编辑',
      onClick: () => handleEdit(orchestration),
    },
    {
      key: 'execute',
      icon: <PlayCircleOutlined />,
      label: '执行',
      onClick: () => handleExecute(orchestration),
    },
    {
      type: 'divider',
    },
    {
      key: 'delete',
      icon: <DeleteOutlined />,
      label: '删除',
      danger: true,
      onClick: () => handleDelete(orchestration),
    },
  ];

  const columns = [
    {
      title: '名称',
      dataIndex: 'displayName',
      key: 'displayName',
      width: 200,
      render: (text: string, record: OrchestrationConfig) => (
        <div>
          <div style={{ fontWeight: 500 }}>{text}</div>
          <div style={{ fontSize: '12px', color: '#999' }}>{record.name}</div>
        </div>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: 300,
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <span>{text}</span>
        </Tooltip>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 120,
      render: (type: OrchestrationType) => getOrchestrationTypeTag(type),
    },
    {
      title: '节点数',
      key: 'nodeCount',
      width: 80,
      render: (_: any, record: OrchestrationConfig) => (
        <span>{record.nodes.length}</span>
      ),
    },
    {
      title: '连接数',
      key: 'edgeCount',
      width: 80,
      render: (_: any, record: OrchestrationConfig) => (
        <span>{record.edges.length}</span>
      ),
    },
    {
      title: '入口点',
      dataIndex: 'entryPoint',
      key: 'entryPoint',
      width: 120,
      render: (entryPoint: string, record: OrchestrationConfig) => {
        if (!entryPoint) return '-';
        const entryNode = record.nodes.find(
          (node: any) =>
            (node.agentId && node.agentId === entryPoint) ||
            (node.id && node.id === entryPoint)
        );
        return entryNode ? entryNode.displayName : entryPoint;
      },
    },
    {
      title: '操作',
      key: 'actions',
      fixed: 'right' as const,
      width: 120,
      render: (_: any, record: OrchestrationConfig) => (
        <Space>
          <Tooltip title="执行">
            <Button 
              type="text" 
              icon={<PlayCircleOutlined />} 
              onClick={() => handleExecute(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button 
              type="text" 
              icon={<EditOutlined />} 
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Dropdown 
            menu={{ items: getActionMenuItems(record) }}
            trigger={['click']}
          >
            <Button type="text" icon={<MoreOutlined />} />
          </Dropdown>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <div style={{ marginBottom: '16px' }}>
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            marginBottom: '16px' 
          }}>
            <Title level={2} style={{ margin: 0 }}>Multi-Agent 编排管理</Title>
          </div>
          <div style={{ marginBottom: '16px' }}>
            <Button 
              type="primary" 
              icon={<PlusOutlined />} 
              onClick={handleCreateNew}
            >
              新建编排
            </Button>
          </div>
        </div>
        
        <Table 
          columns={columns} 
          dataSource={orchestrations as OrchestrationConfig[]} 
          rowKey="id" 
          loading={loading}
          scroll={{ x: 1200 }}
          pagination={{
            defaultPageSize: 10,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50'],
            showTotal: (total) => `共 ${total} 条记录`
          }}
        />
      </Card>


      {/* Execution Modal */}
      <Modal
        title="执行编排"
        open={executionModalVisible}
        onCancel={() => {
          setExecutionModalVisible(false);
          setCurrentOrchestration(null);
        }}
        width="80vw"
        style={{ top: 20 }}
        footer={null}
        destroyOnHidden
      >
        <OrchestrationExecution />
      </Modal>
    </div>
  );
};
