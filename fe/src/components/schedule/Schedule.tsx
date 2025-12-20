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
} from 'antd';
import { 
  PlusOutlined, 
  EditOutlined, 
  DeleteOutlined 
} from '@ant-design/icons';
import { isValidCron } from 'cron-validator';
import { useAgentStore } from '../../store/agentStore';
import { useScheduleStore } from '../../store/scheduleStore';
import type { Agent } from '../../services/api';

const { Title } = Typography;
const { Option } = Select;

interface ScheduleItem {
  id: string;
  agentId: string;
  agentUserId?: string;
  agentName: string;
  cronExpression: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  user_message?: string;
}

export const Schedule: React.FC = () => {
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();
  const { agents, fetchAgents } = useAgentStore();
  const { 
    schedules, 
    loading, 
    createModalVisible,
    editModalVisible,
    selectedSchedule, 
    fetchSchedules,
    setCreateModalVisible,
    setEditModalVisible,
    setSelectedSchedule,
    createSchedule,
    updateSchedule,
    deleteSchedule
  } = useScheduleStore();

  // Load data on component mount
  useEffect(() => {
    fetchAgents();
    fetchSchedules();
  }, [fetchAgents, fetchSchedules]);

  // Reset form when modal is opened
  useEffect(() => {
    if (createModalVisible) {
      form.resetFields();
    }
  }, [createModalVisible, form]);

  // Set edit form values when selected schedule changes
  useEffect(() => {
    if (selectedSchedule && editModalVisible) {
      // Construct composite key for the select value
      const compositeKey = `${selectedSchedule.agentUserId || 'public'}#${selectedSchedule.agentId}`;
      editForm.setFieldsValue({
        agentId: compositeKey,
        cronExpression: selectedSchedule.cronExpression,
        user_message: selectedSchedule.user_message
      });
    }
  }, [selectedSchedule, editModalVisible, editForm]);

  // Handle create schedule form submission
  const handleCreateSchedule = async (values: { agentId: string; cronExpression: string; user_message?: string }) => {
    // Parse the composite key (creator#agentId)
    const [agentUserId, agentId] = values.agentId.split('#');
    
    if (!agentUserId || !agentId) {
      Modal.error({
        title: '错误',
        content: '无效的Agent选择'
      });
      return;
    }
    
    await createSchedule({
      agentId,
      agentUserId,
      cronExpression: values.cronExpression,
      user_message: values.user_message
    });
    form.resetFields();
  };

  // Handle edit schedule
  const handleEditSchedule = (schedule: ScheduleItem) => {
    setSelectedSchedule(schedule);
    setEditModalVisible(true);
  };

  // Handle edit schedule form submission
  const handleUpdateSchedule = async (values: { agentId: string; cronExpression: string; user_message?: string }) => {
    if (!selectedSchedule) return;
    
    // Parse the composite key (creator#agentId)
    const [agentUserId, agentId] = values.agentId.split('#');
    
    if (!agentUserId || !agentId) {
      Modal.error({
        title: '错误',
        content: '无效的Agent选择'
      });
      return;
    }
    
    await updateSchedule({
      ...selectedSchedule,
      agentId,
      agentUserId,
      cronExpression: values.cronExpression,
      user_message: values.user_message
    });
    
    editForm.resetFields();
  };

  // Handle delete schedule with confirmation
  const handleDeleteScheduleWithConfirm = (id: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个调度任务吗？此操作不可逆。',
      okText: '确认',
      cancelText: '取消',
      onOk: () => deleteSchedule(id)
    });
  };

  // Table columns
  const columns = [
    {
      title: 'Agent名称',
      dataIndex: 'agentName',
      key: 'agentName',
      width: 150,
    },
    {
      title: 'Cron表达式',
      dataIndex: 'cronExpression',
      key: 'cronExpression',
      width: 200,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 150,
    },
    {
      title: '更新时间',
      dataIndex: 'updatedAt',
      key: 'updatedAt',
      width: 150,
    },
    {
      title: '操作',
      key: 'actions',
      fixed: 'right' as const,
      width: 120,
      render: (_: unknown, record: ScheduleItem) => (
        <Space>
          <Button 
            type="text" 
            icon={<EditOutlined />} 
            onClick={() => handleEditSchedule(record)} 
          />
          <Button 
            type="text" 
            danger 
            icon={<DeleteOutlined />} 
            onClick={() => handleDeleteScheduleWithConfirm(record.id)} 
          />
        </Space>
      ),
    },
  ];

  // Create schedule form
  const createScheduleForm = (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleCreateSchedule}
    >
      <Form.Item
        name="agentId"
        label="选择Agent"
        rules={[{ required: true, message: '请选择Agent' }]}
      >
        <Select placeholder="选择要调度的Agent" showSearch optionFilterProp="children">
          {agents.map((agent: Agent) => {
            // Create composite key: creator#agentId
            const compositeKey = `${agent.creator || 'public'}#${agent.id}`;
            return (
              <Option key={compositeKey} value={compositeKey}>
                {agent.display_name}
              </Option>
            );
          })}
        </Select>
      </Form.Item>
      
      <Form.Item
        name="cronExpression"
        label="Cron表达式"
        rules={[
          { required: true, message: '请输入Cron表达式' },
          {
            validator: (_, value) => {
              if (!value) {
                return Promise.resolve();
              }
              
              const parts = value.trim().split(/\s+/);
              
              // Check if it has exactly 5 parts
              if (parts.length !== 5) {
                return Promise.reject(new Error('Cron表达式必须包含5个字段: 分 时 日 月 周'));
              }
              
              // Check if either day-of-month or day-of-week is '?'
              if (parts[2] !== '?' && parts[4] !== '?') {
                return Promise.reject(new Error('日字段或周字段必须有一个为 ?'));
              }
              
              // Validate using cron-validator
              const isValid = isValidCron(value, { 
                alias: true,
                allowBlankDay: true,
                allowSevenAsSunday: true
              });
              
              if (!isValid) {
                return Promise.reject(new Error('Cron表达式格式不正确'));
              }
              
              return Promise.resolve();
            }
          }
        ]}
        help="格式: 分 时 日 月 周。支持: * (任意), ? (不指定), */n (步长), n-m (范围), n,m (列表)。例如: '0 8 ? * 1' (每周一8点), '*/5 * ? * *' (每5分钟), '0 9-17 ? * 1-5' (工作日9-17点)"
      >
        <Input placeholder="例如: 0 8 ? * 1 或 */5 * ? * * 或 0 9-17 ? * 1-5" />
      </Form.Item>
      
      <Form.Item
        name="user_message"
        label="Agent消息"
        help="调度任务执行时发送给Agent的消息"
      >
        <Input.TextArea placeholder="请输入要发送给Agent的消息" rows={4} />
      </Form.Item>
    </Form>
  );

  // Edit schedule form
  const editScheduleForm = (
    <Form
      form={editForm}
      layout="vertical"
      onFinish={handleUpdateSchedule}
    >
      <Form.Item
        name="agentId"
        label="选择Agent"
        rules={[{ required: true, message: '请选择Agent' }]}
      >
        <Select placeholder="选择要调度的Agent" showSearch optionFilterProp="children">
          {agents.map((agent: Agent) => {
            // Create composite key: creator#agentId
            const compositeKey = `${agent.creator || 'public'}#${agent.id}`;
            return (
              <Option key={compositeKey} value={compositeKey}>
                {agent.display_name}
              </Option>
            );
          })}
        </Select>
      </Form.Item>
      
      <Form.Item
        name="cronExpression"
        label="Cron表达式"
        rules={[
          { required: true, message: '请输入Cron表达式' },
          {
            validator: (_, value) => {
              if (!value) {
                return Promise.resolve();
              }
              
              const parts = value.trim().split(/\s+/);
              
              // Check if it has exactly 5 parts
              if (parts.length !== 5) {
                return Promise.reject(new Error('Cron表达式必须包含5个字段: 分 时 日 月 周'));
              }
              
              // Check if either day-of-month or day-of-week is '?'
              if (parts[2] !== '?' && parts[4] !== '?') {
                return Promise.reject(new Error('日字段或周字段必须有一个为 ?'));
              }
              
              // Validate using cron-validator
              const isValid = isValidCron(value, { 
                alias: true,
                allowBlankDay: true,
                allowSevenAsSunday: true
              });
              
              if (!isValid) {
                return Promise.reject(new Error('Cron表达式格式不正确'));
              }
              
              return Promise.resolve();
            }
          }
        ]}
        help="格式: 分 时 日 月 周。支持: * (任意), ? (不指定), */n (步长), n-m (范围), n,m (列表)。例如: '0 8 ? * 1' (每周一8点), '*/5 * ? * *' (每5分钟), '0 9-17 ? * 1-5' (工作日9-17点)"
      >
        <Input placeholder="例如: 0 8 ? * 1 或 */5 * ? * * 或 0 9-17 ? * 1-5" />
      </Form.Item>
      
      <Form.Item
        name="user_message"
        label="Agent消息"
        help="调度任务执行时发送给Agent的消息"
      >
        <Input.TextArea placeholder="请输入要发送给Agent的消息" rows={4} />
      </Form.Item>
    </Form>
  );

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <Title level={2}>Agent 调度管理</Title>
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
          dataSource={schedules} 
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
        
        {/* Create Schedule Modal */}
        <Modal
          title="新增调度任务"
          open={createModalVisible}
          onCancel={() => setCreateModalVisible(false)}
          onOk={() => form.submit()}
          width={500}
          okText="创建"
          cancelText="取消"
        >
          {createScheduleForm}
        </Modal>
        
        {/* Edit Schedule Modal */}
        <Modal
          title="编辑调度任务"
          open={editModalVisible}
          onCancel={() => {
            setEditModalVisible(false);
            setSelectedSchedule(null);
          }}
          onOk={() => editForm.submit()}
          width={500}
          okText="保存"
          cancelText="取消"
        >
          {editScheduleForm}
        </Modal>
      </Card>
    </div>
  );
};
