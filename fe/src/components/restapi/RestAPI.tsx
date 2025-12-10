import React, { useEffect } from 'react';
import { Card, Typography, Table, Button, Space, Modal, Form, Input, Select, message } from 'antd';
import { PlusOutlined, EyeOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useRestApiStore } from '../../store/restApiStore';
import type { RestAPI as RestAPIType } from '../../types';

const { Title } = Typography;
const { TextArea } = Input;

export const RestAPI: React.FC = () => {
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  
  const { 
    restApis, 
    loading, 
    createModalVisible, 
    editModalVisible,
    detailModalVisible, 
    deleteModalVisible,
    selectedApi,
    fetchRestAPIs,
    setCreateModalVisible,
    setEditModalVisible,
    setDetailModalVisible,
    setDeleteModalVisible,
    createRestAPI,
    updateRestAPI,
    deleteRestAPI,
    handleViewApi,
    handleEditApi,
    handleDeleteApi
  } = useRestApiStore();
  
  useEffect(() => {
    if (createModalVisible) createForm.resetFields();
  }, [createModalVisible, createForm]);
  
  useEffect(() => {
    if (selectedApi && editModalVisible) {
      // Stringify endpoints for the TextArea
      const formValues = {
        ...selectedApi,
        endpoints: JSON.stringify(selectedApi.endpoints, null, 2)
      };
      editForm.setFieldsValue(formValues);
    }
  }, [selectedApi, editModalVisible, editForm]);
  
  useEffect(() => {
    fetchRestAPIs();
  }, [fetchRestAPIs]);
  
  const handleCreateRestAPI = async (values: Omit<RestAPIType, 'api_id' | 'user_id'>) => {
    try {
      // Parse endpoints JSON string to array
      const parsedValues = {
        ...values,
        endpoints: typeof values.endpoints === 'string' 
          ? JSON.parse(values.endpoints) 
          : values.endpoints
      };
      await createRestAPI(parsedValues);
      createForm.resetFields();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Invalid JSON format in endpoints';
      message.error(errorMessage);
    }
  };
  
  const handleUpdateRestAPI = async (values: Omit<RestAPIType, 'api_id' | 'user_id'>) => {
    try {
      // Parse endpoints JSON string to array
      const parsedValues = {
        ...values,
        endpoints: typeof values.endpoints === 'string' 
          ? JSON.parse(values.endpoints) 
          : values.endpoints
      };
      await updateRestAPI({ ...parsedValues, api_id: selectedApi?.api_id });
      editForm.resetFields();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Invalid JSON format in endpoints';
      message.error(errorMessage);
    }
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      width: 150,
    },
    {
      title: 'Base URL',
      dataIndex: 'base_url',
      key: 'base_url',
      width: 250,
    },
    {
      title: 'Auth Type',
      dataIndex: 'auth_type',
      key: 'auth_type',
      width: 100,
    },
    {
      title: 'Endpoints',
      key: 'endpoints',
      width: 100,
      render: (_: unknown, record: RestAPIType) => record.endpoints?.length || 0,
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: RestAPIType) => (
        <Space size="small">
          <Button type="link" icon={<EyeOutlined />} onClick={() => handleViewApi(record)} />
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEditApi(record)} />
          <Button type="link" danger icon={<DeleteOutlined />} onClick={() => handleDeleteApi(record)} />
        </Space>
      ),
    },
  ];

  return (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4}>REST API Management</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
          Add REST API
        </Button>
      </div>
      
      <Table
        columns={columns}
        dataSource={restApis}
        rowKey="api_id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />

      {/* Create Modal */}
      <Modal
        title="Create REST API"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        onOk={() => createForm.submit()}
        width={800}
      >
        <Form form={createForm} layout="vertical" onFinish={handleCreateRestAPI}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="base_url" label="Base URL" rules={[{ required: true }]}>
            <Input placeholder="https://api.example.com" />
          </Form.Item>
          <Form.Item name="auth_type" label="Auth Type" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="none">None</Select.Option>
              <Select.Option value="bearer">Bearer Token</Select.Option>
              <Select.Option value="api_key">API Key</Select.Option>
              <Select.Option value="basic">Basic Auth</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(prev, curr) => prev.auth_type !== curr.auth_type}>
            {({ getFieldValue }) => 
              getFieldValue('auth_type') !== 'none' && (
                <>
                  <Form.Item name={['auth_config', 'header']} label="Auth Header">
                    <Input placeholder="Authorization" />
                  </Form.Item>
                  <Form.Item name={['auth_config', 'value']} label="Auth Value" rules={[{ required: true }]}>
                    <Input.Password placeholder="Bearer token123..." />
                  </Form.Item>
                </>
              )
            }
          </Form.Item>
          <Form.Item name="endpoints" label="Endpoints (JSON)" rules={[{ required: true }]}>
            <TextArea rows={10} placeholder='[{"path": "/api/resource", "method": "GET", "tool_name": "get_resource", "tool_description": "Get resource"}]' />
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit Modal */}
      <Modal
        title="Edit REST API"
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        onOk={() => editForm.submit()}
        width={800}
      >
        <Form form={editForm} layout="vertical" onFinish={handleUpdateRestAPI}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="base_url" label="Base URL" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="auth_type" label="Auth Type" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="none">None</Select.Option>
              <Select.Option value="bearer">Bearer Token</Select.Option>
              <Select.Option value="api_key">API Key</Select.Option>
              <Select.Option value="basic">Basic Auth</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(prev, curr) => prev.auth_type !== curr.auth_type}>
            {({ getFieldValue }) => 
              getFieldValue('auth_type') !== 'none' && (
                <>
                  <Form.Item name={['auth_config', 'header']} label="Auth Header">
                    <Input placeholder="Authorization" />
                  </Form.Item>
                  <Form.Item name={['auth_config', 'value']} label="Auth Value">
                    <Input.Password />
                  </Form.Item>
                </>
              )
            }
          </Form.Item>
          <Form.Item name="endpoints" label="Endpoints (JSON)" rules={[{ required: true }]}>
            <TextArea rows={10} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail Modal */}
      <Modal
        title="REST API Details"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[<Button key="close" onClick={() => setDetailModalVisible(false)}>Close</Button>]}
        width={800}
      >
        {selectedApi && (
          <div>
            <p><strong>Name:</strong> {selectedApi.name}</p>
            <p><strong>Base URL:</strong> {selectedApi.base_url}</p>
            <p><strong>Auth Type:</strong> {selectedApi.auth_type}</p>
            <p><strong>Endpoints:</strong></p>
            <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
              {JSON.stringify(selectedApi.endpoints, null, 2)}
            </pre>
          </div>
        )}
      </Modal>

      {/* Delete Modal */}
      <Modal
        title="Delete REST API"
        open={deleteModalVisible}
        onCancel={() => setDeleteModalVisible(false)}
        onOk={deleteRestAPI}
        okText="Delete"
        okButtonProps={{ danger: true }}
      >
        <p>Are you sure you want to delete <strong>{selectedApi?.name}</strong>?</p>
      </Modal>
    </Card>
  );
};
