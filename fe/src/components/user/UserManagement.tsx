import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Space,
  message,
  Popconfirm,
  Tag,
  Card,
  Tabs,
  Row,
  Typography
} from 'antd';
import {
  UserOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  TeamOutlined
} from '@ant-design/icons';
import { userAPI } from '../../services/api';

const { Title } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;

interface User {
  user_id: string;
  username: string;
  email?: string;
  status: string;
  is_admin?: boolean;
  user_groups?: string[];
  created_at: string;
  updated_at: string;
  last_login?: string;
}

interface UserGroup {
  id: string;
  name: string;
  description: string;
  group_key?: string;
}

export const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [userGroups, setUserGroups] = useState<UserGroup[]>([]);
  const [loading, setLoading] = useState(false);
  const [userModalVisible, setUserModalVisible] = useState(false);
  const [groupModalVisible, setGroupModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editingGroup, setEditingGroup] = useState<UserGroup | null>(null);
  const [userForm] = Form.useForm();
  const [groupForm] = Form.useForm();

  // Fetch users
  const fetchUsers = async () => {
    setLoading(true);
    try {
      const response = await userAPI.listUsers();
      // Map UserInfo to User interface
      const mappedUsers: User[] = response.map(user => ({
        user_id: user.user_id,
        username: user.username,
        email: user.email,
        status: user.status,
        is_admin: (user as any).is_admin,
        user_groups: (user as any).user_groups || [],
        created_at: (user as any).created_at || '',
        updated_at: (user as any).updated_at || '',
        last_login: (user as any).last_login
      }));
      setUsers(mappedUsers);
    } catch (error) {
      message.error('Failed to fetch users');
      console.error('Error fetching users:', error);
    } finally {
      setLoading(false);
    }
  };

  // Fetch user groups
  const fetchUserGroups = async () => {
    try {
      const response = await userAPI.listUserGroups();
      if (response.success) {
        setUserGroups(response.data);
      }
    } catch (error) {
      message.error('Failed to fetch user groups');
      console.error('Error fetching user groups:', error);
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchUserGroups();
  }, []);

  // User operations
  const handleEditUser = (user: User) => {
    setEditingUser(user);
    userForm.setFieldsValue({
      username: user.username,
      email: user.email,
      status: user.status,
      is_admin: user.is_admin,
      user_groups: user.user_groups || []
    });
    setUserModalVisible(true);
  };

  const handleDeleteUser = async (userId: string) => {
    try {
      await userAPI.deleteUser(userId);
      message.success('User deleted successfully');
      fetchUsers();
    } catch (error) {
      message.error('Failed to delete user');
      console.error('Error deleting user:', error);
    }
  };

  const handleUserSubmit = async (values: any) => {
    try {
      if (editingUser) {
        await userAPI.updateUser(editingUser.user_id, values);
        message.success('User updated successfully');
      }
      setUserModalVisible(false);
      setEditingUser(null);
      userForm.resetFields();
      fetchUsers();
    } catch (error) {
      message.error('Failed to save user');
      console.error('Error saving user:', error);
    }
  };

  // Group operations
  const handleCreateGroup = () => {
    setEditingGroup(null);
    groupForm.resetFields();
    setGroupModalVisible(true);
  };

  const handleEditGroup = (group: UserGroup) => {
    setEditingGroup(group);
    groupForm.setFieldsValue({
      name: group.name,
      description: group.description
    });
    setGroupModalVisible(true);
  };

  const handleDeleteGroup = async (groupId: string) => {
    try {
      await userAPI.deleteUserGroup(groupId);
      message.success('User group deleted successfully');
      fetchUserGroups();
    } catch (error) {
      message.error('Failed to delete user group');
      console.error('Error deleting user group:', error);
    }
  };

  const handleGroupSubmit = async (values: any) => {
    try {
      if (editingGroup) {
        await userAPI.updateUserGroup(editingGroup.id, values);
        message.success('User group updated successfully');
      } else {
        await userAPI.createUserGroup(values);
        message.success('User group created successfully');
      }
      setGroupModalVisible(false);
      setEditingGroup(null);
      groupForm.resetFields();
      fetchUserGroups();
    } catch (error) {
      message.error('Failed to save user group');
      console.error('Error saving user group:', error);
    }
  };

  const userColumns = [
    {
      title: 'Username',
      dataIndex: 'username',
      key: 'username',
      sorter: (a: User, b: User) => a.username.localeCompare(b.username),
      render: (text: string) => (
        <Space>
          <UserOutlined />
          {text}
        </Space>
      ),
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      sorter: (a: User, b: User) => (a.email || '').localeCompare(b.email || ''),
    },
    {
      title: 'Admin',
      dataIndex: 'is_admin',
      key: 'is_admin',
      width: 80,
      sorter: (a: User, b: User) => Number(a.is_admin) - Number(b.is_admin),
      render: (isAdmin: boolean) => (
        <Tag color={isAdmin ? 'red' : 'default'}>
          {isAdmin ? 'Yes' : 'No'}
        </Tag>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      sorter: (a: User, b: User) => a.status.localeCompare(b.status),
      render: (status: string) => (
        <Tag color={status === 'active' ? 'green' : 'red'}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'User Groups',
      dataIndex: 'user_groups',
      key: 'user_groups',
      render: (groups: string[]) => (
        <Space wrap>
          {groups?.map(groupId => {
            const group = userGroups.find(g => g.id === groupId);
            return (
              <Tag key={groupId} color="blue">
                {group?.name || groupId}
              </Tag>
            );
          })}
        </Space>
      ),
    },
    {
      title: 'Last Login',
      dataIndex: 'last_login',
      key: 'last_login',
      sorter: (a: User, b: User) => {
        const dateA = a.last_login ? new Date(a.last_login).getTime() : 0;
        const dateB = b.last_login ? new Date(b.last_login).getTime() : 0;
        return dateA - dateB;
      },
      render: (date: string) => date ? new Date(date).toLocaleString() : 'Never',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: User) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEditUser(record)}
          >
            Edit
          </Button>
          <Popconfirm
            title="Are you sure you want to delete this user?"
            onConfirm={() => handleDeleteUser(record.user_id)}
            okText="Yes"
            cancelText="No"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const groupColumns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => (
        <Space>
          <TeamOutlined />
          {text}
        </Space>
      ),
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: UserGroup) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEditGroup(record)}
          >
            Edit
          </Button>
          <Popconfirm
            title="Are you sure you want to delete this group?"
            onConfirm={() => handleDeleteGroup(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>User Management</Title>
      
      <Tabs defaultActiveKey="users">
        <TabPane tab="Users" key="users">
          <Card>
            <Table
              columns={userColumns}
              dataSource={users}
              rowKey="user_id"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>
        
        <TabPane tab="User Groups" key="groups">
          <Card>
            <Row justify="end" style={{ marginBottom: 16 }}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreateGroup}
              >
                Create Group
              </Button>
            </Row>
            <Table
              columns={groupColumns}
              dataSource={userGroups}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>
      </Tabs>

      {/* User Edit Modal */}
      <Modal
        title={editingUser ? 'Edit User' : 'Create User'}
        open={userModalVisible}
        onCancel={() => {
          setUserModalVisible(false);
          setEditingUser(null);
          userForm.resetFields();
        }}
        footer={null}
      >
        <Form
          form={userForm}
          layout="vertical"
          onFinish={handleUserSubmit}
        >
          <Form.Item
            name="username"
            label="Username"
            rules={[{ required: true, message: 'Please input username!' }]}
          >
            <Input disabled={!!editingUser} />
          </Form.Item>
          
          <Form.Item
            name="email"
            label="Email"
            rules={[{ type: 'email', message: 'Please input valid email!' }]}
          >
            <Input />
          </Form.Item>
          
          <Form.Item
            name="status"
            label="Status"
            rules={[{ required: true, message: 'Please select status!' }]}
          >
            <Select>
              <Option value="active">Active</Option>
              <Option value="inactive">Inactive</Option>
              <Option value="suspended">Suspended</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name="is_admin"
            label="Admin"
          >
            <Select>
              <Option value={true}>Yes</Option>
              <Option value={false}>No</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name="user_groups"
            label="User Groups"
          >
            <Select
              mode="multiple"
              placeholder="Select user groups"
              allowClear
            >
              {userGroups.map(group => (
                <Option key={group.id} value={group.id}>
                  {group.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Save
              </Button>
              <Button onClick={() => {
                setUserModalVisible(false);
                setEditingUser(null);
                userForm.resetFields();
              }}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Group Modal */}
      <Modal
        title={editingGroup ? 'Edit Group' : 'Create Group'}
        open={groupModalVisible}
        onCancel={() => {
          setGroupModalVisible(false);
          setEditingGroup(null);
          groupForm.resetFields();
        }}
        footer={null}
      >
        <Form
          form={groupForm}
          layout="vertical"
          onFinish={handleGroupSubmit}
        >
          <Form.Item
            name="name"
            label="Group Name"
            rules={[{ required: true, message: 'Please input group name!' }]}
          >
            <Input />
          </Form.Item>
          
          {!editingGroup && (
            <Form.Item
              name="group_key"
              label="Group Key"
              rules={[
                { required: true, message: 'Please input group key!' },
                { pattern: /^[a-zA-Z0-9_]+$/, message: 'Group key can only contain letters, numbers, and underscores!' }
              ]}
              help="Group key will be prefixed with 'ugs_'. Only letters, numbers, and underscores are allowed."
            >
              <Input 
                placeholder="e.g., developers, admins, testers"
                addonBefore="ugs_"
              />
            </Form.Item>
          )}
          
          <Form.Item
            name="description"
            label="Description"
          >
            <Input.TextArea rows={3} />
          </Form.Item>
          
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Save
              </Button>
              <Button onClick={() => {
                setGroupModalVisible(false);
                setEditingGroup(null);
                groupForm.resetFields();
              }}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};
