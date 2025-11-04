import React, { useState, useEffect } from 'react';
import { 
  Layout, 
  Tree, 
  Table, 
  Button, 
  Modal, 
  Form, 
  Input, 
  Select, 
  Space, 
  message, 
  Popconfirm,
  Card,
  Typography,
  Row,
  Col,
  InputNumber
} from 'antd';
import { 
  PlusOutlined, 
  EditOutlined, 
  DeleteOutlined, 
  SettingOutlined,
  FolderOutlined,
  FileTextOutlined,
  CloudOutlined
} from '@ant-design/icons';
import type { TreeDataNode } from 'antd';
import { configAPI } from '../../services/api';
import type { 
  SystemConfig, 
  ConfigCategory, 
  ModelProviderConfig,
} from '../../services/api';

const { Sider, Content } = Layout;
const { TextArea } = Input;
const { Option } = Select;
const { Title, Text } = Typography;
// const { TabPane } = Tabs;

interface ConfigFormData {
  key: string;
  value: string;
  key_display_name?: string;
  type: string;
  seq_num: number;
  parent?: string;
}

export const Config: React.FC = () => {
  const [form] = Form.useForm();
  const [modelProviderForm] = Form.useForm();
  const [categoryTree, setCategoryTree] = useState<ConfigCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [configs, setConfigs] = useState<SystemConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [modelProviderModalVisible, setModelProviderModalVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState<SystemConfig | null>(null);
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);

  // Load category tree on component mount
  useEffect(() => {
    loadCategoryTree();
    initializeDefaultCategories();
  }, []);

  // Load configs when category is selected
  useEffect(() => {
    if (selectedCategory) {
      loadConfigsByParent(selectedCategory);
    }
  }, [selectedCategory]);

  const initializeDefaultCategories = async () => {
    try {
      if (categoryTree.length == 0) {
        await configAPI.initDefaultCategories();
      }
    } catch (error) {
      console.error('Error initializing default categories:', error);
    }
  };

  const loadCategoryTree = async () => {
    try {
      setLoading(true);
      const response = await configAPI.getCategoryTree();
      setCategoryTree(response.data);
      
      // Auto expand first level
      const firstLevelKeys = response.data.map((cat: ConfigCategory) => cat.key);
      setExpandedKeys(firstLevelKeys);
      
      // Auto select first category if exists
      if (response.data.length > 0) {
        setSelectedCategory(response.data[0].key);
      }
    } catch (error) {
      message.error('加载配置分类失败');
      console.error('Error loading category tree:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadConfigsByParent = async (parent: string) => {
    try {
      setLoading(true);
      const response = await configAPI.getConfigsByParent(parent);
      setConfigs(response.data);
    } catch (error) {
      message.error('加载配置项失败');
      console.error('Error loading configs:', error);
    } finally {
      setLoading(false);
    }
  };

  // Convert category tree to antd tree data
  const convertToTreeData = (categories: ConfigCategory[]): TreeDataNode[] => {
    return categories.map(category => ({
      key: category.key,
      title: (
        <span>
          <FolderOutlined style={{ marginRight: 8, color: '#1890ff' }} />
          {category.key_display_name || category.key}
        </span>
      ),
      children: category.children.length > 0 ? convertToTreeData(category.children) : undefined,
    }));
  };

  const handleTreeSelect = (selectedKeys: React.Key[]) => {
    if (selectedKeys.length > 0) {
      setSelectedCategory(selectedKeys[0] as string);
    }
  };

  const handleCreateConfig = () => {
    setEditingConfig(null);
    form.resetFields();
    form.setFieldsValue({
      parent: selectedCategory,
      type: 'item',
      seq_num: 0
    });
    setModalVisible(true);
  };

  const handleCreateCategory = (isRoot: boolean = false) => {
    setEditingConfig(null);
    form.resetFields();
    form.setFieldsValue({
      parent: isRoot ? null : selectedCategory,
      type: 'category',
      seq_num: 0,
      value: '{}'
    });
    
    setModalVisible(true);
  };

  const handleCreateModel = () => {
    setEditingConfig(null);
    modelProviderForm.resetFields();
    setModelProviderModalVisible(true);
  };

  const handleEditConfig = (config: SystemConfig) => {
    if(isSubModelProviderCategory) {

      setEditingConfig(config);

      const modelProviderConfig: ModelProviderConfig = JSON.parse(config.value);
      modelProviderForm.setFieldsValue({
        model_key: config.key,
        model_display_name: config.key_display_name,
        model_id: modelProviderConfig.model_id,
        temperature: modelProviderConfig.temperature,
        top_p: modelProviderConfig.top_p,
        max_tokens: modelProviderConfig.max_tokens,
        api_base_url: modelProviderConfig.api_base_url,
        api_key: modelProviderConfig.api_key,
        seq_num: config.seq_num
      });
      setModelProviderModalVisible(true);

    } else {
      setEditingConfig(config);
      form.setFieldsValue(config);
      setModalVisible(true);
    }
    
  };

  const handleDeleteConfig = async (config: SystemConfig) => {
    try {
      await configAPI.deleteConfig(config.key);
      message.success('配置删除成功');
      loadConfigsByParent(selectedCategory);
      loadCategoryTree(); // Refresh tree
    } catch (error) {
      message.error('配置删除失败');
      console.error('Error deleting config:', error);
    }
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      const configData: ConfigFormData = {
        ...values,
        seq_num: values.seq_num || 0
      };

      if (editingConfig) {
        // Update existing config
        await configAPI.updateConfig(editingConfig.key, configData);
        message.success('配置更新成功');
      } else {
        // Create new config
        await configAPI.createConfig(configData);
        message.success('配置创建成功');
      }

      setModalVisible(false);
      loadConfigsByParent(selectedCategory);
      if(!values.parent) {
        loadCategoryTree(); // Refresh tree in case new category was added
      }
    } catch (error) {
      message.error(editingConfig ? '配置更新失败' : '配置创建失败');
      console.error('Error saving config:', error);
    }
  };

  const handleModelModalOk = async () => {
    try {
      const values = await modelProviderForm.validateFields();

      const modelConfig: ConfigFormData = {
        key: values.model_key,
        key_display_name: values.model_display_name,
        value: JSON.stringify({
          model_id: values.model_id,
          temperature: values.temperature,
          top_p: values.top_p,
          max_tokens: values.max_tokens,
          api_base_url: values.api_base_url,
          api_key: values.api_key,
          seq_num: values.seq_num
        } as ModelProviderConfig),
        type: 'item',
        seq_num: values.seq_num,
        parent: selectedCategory 
      };

      if(editingConfig) {
         await configAPI.updateConfig(editingConfig.key, modelConfig);
         message.success('配置更新成功');
         setEditingConfig(null);
      } else {
        await configAPI.createConfig(modelConfig);
        message.success('模型创建成功');
      }

      setModelProviderModalVisible(false);
      loadConfigsByParent(selectedCategory);

    } catch (error) {
      message.error('模型创建失败');
      console.error('Error creating model provider:', error);
    }
  };

  const handleModalCancel = () => {
    setModalVisible(false);
    form.resetFields();
    setEditingConfig(null);
  };

  const handleModelModalCancel = () => {
    setModelProviderModalVisible(false);
    modelProviderForm.resetFields();
  };

  const renderConfigValue = (value: string, config: SystemConfig) => {
    if (config.parent?.startsWith('model_providers.') && config.type === 'item') {
      try {
        const parsedValue = JSON.parse(value);
        return (
          <div>
            <div><strong>Model ID:</strong> {parsedValue.model_id}</div>
            <div><strong>Temperature:</strong> {parsedValue.temperature}</div>
            <div><strong>Max Tokens:</strong> {parsedValue.max_tokens}</div>
            {parsedValue.api_base_url && <div><strong>API Base URL:</strong> {parsedValue.api_base_url}</div>}
            {parsedValue.api_key && <div><strong>API Key:</strong> {parsedValue.api_key.substring(0, 10)}...</div>}
          </div>
        );
      } catch (e) {
        return value;
      }
    }
    return (
      <div style={{ 
        maxWidth: '200px', 
        overflow: 'hidden', 
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap'
      }}>
        {value}
      </div>
    );
  };

  const columns = [
    {
      title: '配置项',
      dataIndex: 'key_display_name',
      key: 'key_display_name',
      width: 300,
      render: (text: string, record: SystemConfig) => (
        <div>
          <div style={{ fontWeight: 500 }}>{text || record.key}</div>
          <div style={{ fontSize: '12px', color: '#999' }}>{record.key}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {record.type === 'category' ? '分类' : '配置项'}
          </div>
        </div>
      ),
    },
    {
      title: '配置值',
      dataIndex: 'value',
      key: 'value',
      render: (text: string, record: SystemConfig) => renderConfigValue(text, record),
    },
    {
      title: '排序',
      dataIndex: 'seq_num',
      key: 'seq_num',
      width: 80,
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: SystemConfig) => (
        <Space>
          <Button 
            type="link" 
            size="small" 
            icon={<EditOutlined />}
            onClick={() => handleEditConfig(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个配置项吗？"
            onConfirm={() => handleDeleteConfig(record)}
            okText="确定"
            cancelText="取消"
          >
            <Button 
              type="link" 
              size="small" 
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const getCurrentCategoryInfo = () => {
    const findCategory = (categories: ConfigCategory[], targetCategory: string): ConfigCategory | null => {
      for (const category of categories) {
        if (category.key === targetCategory) {
          return category;
        }
        if (category.children.length > 0) {
          const found = findCategory(category.children, targetCategory);
          if (found) return found;
        }
      }
      return null;
    };

    return findCategory(categoryTree, selectedCategory);
  };

  const currentCategoryInfo = getCurrentCategoryInfo();
  // const isModelProvidersCategory = selectedCategory === 'model_providers';
  const isSubModelProviderCategory = currentCategoryInfo?.parent === 'model_providers'

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '16px 24px', borderBottom: '1px solid #f0f0f0' }}>
        <Title level={4} style={{ margin: 0 }}>
          <SettingOutlined style={{ marginRight: 8 }} />
          系统配置管理
        </Title>
      </div>
      
      <Layout style={{ flex: 1 }}>
        <Sider 
          width={250} 
          theme="light" 
          style={{ 
            borderRight: '1px solid #f0f0f0',
            overflow: 'auto'
          }}
        >
          <div style={{ padding: '16px' }}>
            <div style={{ marginBottom: '16px' }}>
              <Text strong>配置分类</Text>
              <Button 
                  icon={<PlusOutlined />}
                  style={{marginLeft: '16px'}}
                  onClick={()=> handleCreateCategory(true)}
                >
              </Button>
              <Button 
                  style={{marginLeft: '16px'}}
                  icon={<DeleteOutlined />}
                >
              </Button>
            </div>
            <Tree
              treeData={convertToTreeData(categoryTree)}
              onSelect={handleTreeSelect}
              selectedKeys={selectedCategory ? [selectedCategory] : []}
              expandedKeys={expandedKeys}
              onExpand={(keys) => setExpandedKeys(keys as string[])}
              showLine={{ showLeafIcon: false }}
            />
          </div>
        </Sider>
        
        <Content style={{ padding: '16px' }}>
          {selectedCategory ? (
            <Card>
              <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <Title level={5} style={{ margin: 0 }}>
                    {currentCategoryInfo?.key_display_name || selectedCategory}
                  </Title>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    分类: {selectedCategory}
                  </Text>
                </div>
                <Space>
                  {
                    isSubModelProviderCategory ? (
                      <Button 
                      type="primary" 
                      icon={<CloudOutlined />}
                      onClick={handleCreateModel}
                      >
                        新增模型
                      </Button>
                    ) : (
                      <>
                        <Button 
                          icon={<FolderOutlined />}
                          onClick={() => handleCreateCategory()}
                        >
                          新增分类
                        </Button>
                        <Button 
                          type="primary" 
                          icon={<PlusOutlined />}
                          onClick={handleCreateConfig}
                        >
                          新增配置
                        </Button>
                      </>
                    )
                  }
                </Space>
              </div>
              
              <Table
                columns={columns}
                dataSource={configs}
                rowKey={(record) => record.key}
                loading={loading}
                pagination={{
                  pageSize: 10,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total) => `共 ${total} 条记录`,
                }}
              />
            </Card>
          ) : (
            <div style={{ 
              textAlign: 'center', 
              padding: '60px 20px',
              color: '#999'
            }}>
              <FileTextOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
              <div>请选择左侧的配置分类</div>
            </div>
          )}
        </Content>
      </Layout>

      {/* 通用配置模态框 */}
      <Modal
        title={editingConfig ? '编辑配置' : '新增配置'}
        open={modalVisible}
        onOk={handleModalOk}
        onCancel={handleModalCancel}
        width={600}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            seq_num: 0,
            type: 'item'
          }}
        >
          <Form.Item
            name="key"
            label="配置Key"
            rules={[{ required: true, message: '请输入配置Key' }]}
          >
            <Input placeholder="例如: database.host, api.timeout" disabled={!!editingConfig} />
          </Form.Item>
          
          <Form.Item
            name="key_display_name"
            label="显示名称"
          >
            <Input placeholder="例如: 数据库主机, API超时时间" />
          </Form.Item>
          
          <Form.Item
            name="type"
            label="类型"
            rules={[{ required: true, message: '请选择类型' }]}
          >
            <Select>
              <Option value="category">分类</Option>
              <Option value="item">配置项</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name="value"
            label="配置值"
            rules={[{ required: true, message: '请输入配置值' }]}
          >
            <TextArea rows={4} placeholder="请输入配置值，分类请使用 {}" />
          </Form.Item>
          
          <Form.Item
            name="parent"
            label="父级分类"
          >
            <Input placeholder="例如: database, model_providers" />
          </Form.Item>
          
          <Form.Item
            name="seq_num"
            label="排序序号"
          >
            <InputNumber min={0} placeholder="0" style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 模型提供商专用模态框 */}
      <Modal
        title="新增模型配置"
        open={modelProviderModalVisible}
        onOk={handleModelModalOk}
        onCancel={handleModelModalCancel}
        width={700}
        destroyOnHidden
      >
        <Form
          form={modelProviderForm}
          layout="vertical"
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="model_key"
                label="Model Key"
                rules={[{ required: true, message: '请输入Model Key' }]}
              >
                <Input placeholder="例如: claude-3.7, claude-4.0" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="model_display_name"
                label="Model 显示名称"
                rules={[{ required: true, message: '请输入显示名称' }]}
              >
                <Input placeholder="例如: claude-3.7, claude-4.0" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="model_id"
                label="模型ID"
                rules={[{ required: true, message: '请输入模型ID' }]}
              >
                <Input placeholder="例如: gpt-4, claude-3-sonnet" />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item
                name="seq_num"
                label="排序序号"
              >
                <InputNumber min={0} placeholder="0" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          
          
          
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="temperature"
                label="Temperature"
                // rules={[{ required: true, message: '请输入Temperature' }]}
              >
                <InputNumber min={0} max={2} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="top_p"
                label="Top P"
                // rules={[{ required: true, message: '请输入Top P' }]}
              >
                <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="max_tokens"
                label="Max Tokens"
                // rules={[{ required: true, message: '请输入Max Tokens' }]}
              >
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          
          <Form.Item
            name="api_base_url"
            label="API Base URL"
          >
            <Input placeholder="例如: https://api.openai.com/v1" />
          </Form.Item>
          
          <Form.Item
            name="api_key"
            label="API Key"
          >
            <Input.Password placeholder="请输入API密钥" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};
