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
  Tooltip
} from 'antd';
import { 
  PlusOutlined, 
  EyeOutlined, 
  EditOutlined, 
  DeleteOutlined
} from '@ant-design/icons';
import { useMCPStore } from '../../store';
import type { MCPServer } from '../../services/api';

const { Title, Paragraph } = Typography;
const { TextArea } = Input;

export const MCP: React.FC = () => {
  // Form instances - initialized with default values
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  
  // Get state and actions from Zustand store
  const { 
    mcpServers, 
    loading, 
    createModalVisible, 
    editModalVisible,
    detailModalVisible, 
    deleteModalVisible,
    selectedServer,
    fetchMCPServers,
    setCreateModalVisible,
    setEditModalVisible,
    setDetailModalVisible,
    setDeleteModalVisible,
    createMCPServer,
    updateMCPServer,
    deleteMCPServer,
    handleViewServer,
    handleEditServer,
    handleDeleteServer
  } = useMCPStore();
  
  // Reset form when modal is opened
  useEffect(() => {
    if (createModalVisible) {
      createForm.resetFields();
    }
  }, [createModalVisible, createForm]);
  
  // Initialize edit form when selected server changes
  useEffect(() => {
    if (selectedServer && editModalVisible) {
      const formValues = { ...selectedServer } as Record<string, any>;
      if (formValues.headers && typeof formValues.headers === 'object') {
        formValues.headers = JSON.stringify(formValues.headers, null, 2);
      } else {
        formValues.headers = '';
      }
      editForm.setFieldsValue(formValues);
    }
  }, [selectedServer, editModalVisible, editForm]);
  
  // Load data on component mount
  useEffect(() => {
    fetchMCPServers();
  }, [fetchMCPServers]);
  
  // Parse headers string to object, handling edge cases
  const parseHeaders = (headers: string | Record<string, string> | undefined): Record<string, string> | undefined => {
    // Early return for non-string types
    if (!headers || typeof headers !== 'string') {
      return undefined;
    }

    const trimmedHeaders = headers.trim();
    
    // Early return for empty strings
    if (!trimmedHeaders) {
      return undefined;
    }

    // Parse JSON with error handling
    try {
      const parsed = JSON.parse(trimmedHeaders);
      // Validate that parsed result is an object with string values
      if (typeof parsed === 'object' && parsed !== null) {
        return parsed as Record<string, string>;
      }
      return undefined;
    } catch (error) {
      console.error('Failed to parse headers JSON:', error);
      throw new Error('Invalid JSON format in headers field');
    }
  };

  // Handle create MCP server form submission
  const handleCreateMCPServer = async (values: Omit<MCPServer, 'id'>) => {
    try {
      const parsedHeaders = parseHeaders(values.headers as string | undefined);
      
      const payload = {
        ...values,
        ...(parsedHeaders && { headers: parsedHeaders })
      };

      await createMCPServer(payload);
      createForm.resetFields();
    } catch (error) {
      console.error('Failed to create MCP server:', error);
      throw error;
    }
  };
  
  // Handle edit MCP server form submission
  const handleUpdateMCPServer = async (values: MCPServer) => {
    try {
      const parsedHeaders = parseHeaders(values.headers as string | undefined);
      
      const payload = {
        ...values,
        ...(parsedHeaders && { headers: parsedHeaders })
      };

      await updateMCPServer(payload);
      editForm.resetFields();
    } catch (error) {
      console.error('Failed to update MCP server:', error);
      throw error;
    }
  };
  

  // Table columns
  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      resizable: true,
    },
    {
      title: '描述',
      dataIndex: 'desc',
      key: 'desc',
      width: 250,
      resizable: true,
    },
    {
      title: '主机地址',
      dataIndex: 'host',
      key: 'host',
      width: 250,
      resizable: true,
      ellipsis: true,
      render: (host: string) => (
        <Tooltip title={host}>
          <span>{host}</span>
        </Tooltip>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      fixed: 'right' as const,
      width: 120,
      render: (_: unknown, record: MCPServer) => (
        <Space>
          <Tooltip title="查看">
            <Button 
              type="text" 
              icon={<EyeOutlined />} 
              onClick={() => handleViewServer(record)} 
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button 
              type="text" 
              icon={<EditOutlined />} 
              onClick={() => handleEditServer(record)} 
            />
          </Tooltip>
          <Tooltip title="删除">
            <Button 
              type="text" 
              danger 
              icon={<DeleteOutlined />} 
              onClick={() => handleDeleteServer(record)} 
            />
          </Tooltip>
        </Space>
      ),
    },
  ];
  
  // Create MCP server form
  const createMCPServerForm = (
    <Form
      form={createForm}
      layout="vertical"
      onFinish={handleCreateMCPServer}
      initialValues={{
        name: '',
        desc: '',
        host: '',
        headers: '',
      }}
    >
      <Form.Item
        name="name"
        label="MCP服务器名称"
        rules={[
          { required: true, message: '请输入MCP服务器名称' },
          { max: 100, message: '名称不能超过100个字符' },
        ]}
      >
        <Input placeholder="例如: MySQL Server" />
      </Form.Item>
      
      <Form.Item
        name="desc"
        label="描述"
        rules={[
          { required: true, message: '请输入描述' },
        ]}
      >
        <TextArea rows={4} placeholder="描述MCP服务器的功能和能力" />
      </Form.Item>
      
      <Form.Item
        name="host"
        label="主机地址"
        rules={[
          { required: true, message: '请输入主机地址' },
        ]}
      >
        <Input placeholder="例如: http://localhost:8001" />
      </Form.Item>
      
      <Form.Item
        name="headers"
        label="请求头 (JSON格式)"
        rules={[
          { 
            validator: (_, value) => {
              if (!value) return Promise.resolve();
              try {
                JSON.parse(value);
                return Promise.resolve();
              } catch {
                return Promise.reject(new Error('请输入有效的JSON格式'));
              }
            }
          }
        ]}
      >
        <TextArea 
          rows={3} 
          placeholder='例如: {"Authorization": "Bearer token123"}' 
        />
      </Form.Item>
    </Form>
  );
  
  // MCP server detail modal content
  const serverDetailContent = selectedServer && (
    <div style={{ maxHeight: '70vh', overflow: 'auto' }}>
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ borderBottom: '1px solid #f0f0f0', paddingBottom: '10px' }}>基本信息</h3>
        <p><strong>ID:</strong> {selectedServer.id}</p>
        <p><strong>名称:</strong> {selectedServer.name}</p>
        <p><strong>描述:</strong> {selectedServer.desc}</p>
        <p><strong>主机地址:</strong> {selectedServer.host}</p>
        {selectedServer.headers && (
          <p><strong>请求头:</strong> <pre>{JSON.stringify(selectedServer.headers, null, 2)}</pre></p>
        )}
      </div>
    </div>
  );
  
  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <Title level={2}>MCP 服务器管理</Title>
          <Button 
            type="primary" 
            icon={<PlusOutlined />} 
            onClick={() => setCreateModalVisible(true)}
          >
            新增
          </Button>
        </div>
        
        <Paragraph>
          管理和监控您的Model Context Protocol (MCP) 服务器。
        </Paragraph>
        
        <Table 
          columns={columns} 
          dataSource={mcpServers} 
          rowKey="id" 
          loading={loading}
          scroll={{ x: 1000 }}
          pagination={{
            defaultPageSize: 10,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50'],
            showTotal: (total) => `共 ${total} 条记录`
          }}
        />
        
        {/* Create MCP Server Modal */}
        <Modal
          title="新增 MCP 服务器"
          open={createModalVisible}
          onCancel={() => setCreateModalVisible(false)}
          onOk={() => createForm.submit()}
          width={700}
          okText="创建"
          cancelText="取消"
        >
          {createMCPServerForm}
        </Modal>
        
        {/* Edit MCP Server Modal */}
        <Modal
          title="编辑 MCP 服务器"
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
            onFinish={handleUpdateMCPServer}
          >
            <Form.Item name="id" hidden>
              <Input />
            </Form.Item>
            
            <Form.Item
              name="name"
              label="MCP服务器名称"
              rules={[
                { required: true, message: '请输入MCP服务器名称' },
                { max: 100, message: '名称不能超过100个字符' },
              ]}
            >
              <Input placeholder="例如: MySQL Server" />
            </Form.Item>
            
            <Form.Item
              name="desc"
              label="描述"
              rules={[
                { required: true, message: '请输入描述' },
              ]}
            >
              <TextArea rows={4} placeholder="描述MCP服务器的功能和能力" />
            </Form.Item>
            
            <Form.Item
              name="host"
              label="主机地址"
              rules={[
                { required: true, message: '请输入主机地址' },
              ]}
            >
              <Input placeholder="例如: http://localhost:8001" />
            </Form.Item>
            
            <Form.Item
              name="headers"
              label="请求头 (JSON格式)"
              rules={[
                { 
                  validator: (_, value) => {
                    if (!value) return Promise.resolve();
                    try {
                      JSON.parse(value);
                      return Promise.resolve();
                    } catch {
                      return Promise.reject(new Error('请输入有效的JSON格式'));
                    }
                  }
                }
              ]}
            >
              <TextArea 
                rows={3} 
                placeholder='例如: {"Authorization": "Bearer token123"}' 
              />
            </Form.Item>
          </Form>
        </Modal>
        
        {/* MCP Server Detail Modal */}
        <Modal
          title="MCP 服务器详情"
          open={detailModalVisible}
          onCancel={() => setDetailModalVisible(false)}
          width={700}
          footer={[
            <Button key="close" onClick={() => setDetailModalVisible(false)}>
              关闭
            </Button>
          ]}
        >
          {serverDetailContent}
        </Modal>

        <Modal
          title="确认删除"
          open={deleteModalVisible}
          onCancel={() => setDeleteModalVisible(false)}
          onOk={() => {
            console.log('Deleting server:', selectedServer?.id);
            deleteMCPServer(selectedServer?.id || '');
          }}
          okText="确认"
          cancelText="取消"
        >
          <p>确定要删除这个 {selectedServer ? "["+ selectedServer.name +"]" : "MCP"} 服务器吗？</p>
          <p>请注意，删除后无法恢复，请谨慎操作。</p>

        </Modal>
      </Card>
    </div>
  );
};
