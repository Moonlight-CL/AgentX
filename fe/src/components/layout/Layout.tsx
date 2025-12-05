import React, { useEffect, useState } from 'react';
import { Layout as AntLayout, Menu, Dropdown, Avatar } from 'antd';
import { 
  CommentOutlined, 
  SettingOutlined, 
  AppstoreOutlined,
  MenuUnfoldOutlined,
  MenuFoldOutlined,
  ScheduleOutlined,
  UserOutlined,
  LogoutOutlined,
  ControlOutlined,
  ApiOutlined
} from '@ant-design/icons';
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useNavigate } from 'react-router-dom';
import { useMsal } from '@azure/msal-react';
import { Chat, ChatDetail } from '../chat';
import { AgentHub } from '../agent';
import { MCP } from '../mcp/MCP';
import { RestAPI } from '../restapi';
import { Schedule } from '../schedule';
import { Config } from '../config/Config';
import { OrchestrationEditor } from '../orchestration';
import { UseCase } from '../usecase';
import { UserManagement } from '../user';
import { Login, Register, ProtectedRoute } from '../auth';
import { useUserStore } from '../../store/userStore';
import { useUseCaseStore } from '../../store/useCaseStore';
import { userAPI } from '../../services/api';

const { Sider, Content } = AntLayout;

// Internal component that uses useNavigate
const LayoutContent: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [selectedKey, setSelectedKey] = useState('1');
  const navigate = useNavigate();
  const { instance } = useMsal();
  const { isAuthenticated, user, logout } = useUserStore();
  const { 
    primaryCategories,
    secondaryCategories,
    selectedSecondaryCategory,
    fetchPrimaryCategories,
    fetchSecondaryCategories,
    fetchUseCaseItems,
    setSelectedPrimaryCategory,
    setSelectedSecondaryCategory
  } = useUseCaseStore();

  // Fetch use case categories when component mounts
  useEffect(() => {
    fetchPrimaryCategories();
    fetchSecondaryCategories("use_cases")
  }, [fetchPrimaryCategories, fetchSecondaryCategories]);

  // Handle use case menu click
  const handleUseCaseMenuClick = (key: string, keyPath: string[]) => {
    if (keyPath.length === 1) {
      // Primary menu clicked
      setSelectedPrimaryCategory(key);
      setSelectedSecondaryCategory(null);
    } else {
      // Secondary menu clicked
      setSelectedSecondaryCategory(key);
      fetchUseCaseItems(key);
      // Navigate to usecase page
      navigate('/usecase');
    }
  };

  // Update selected key based on current path and use case selection
  useEffect(() => {
    const path = window.location.pathname;
    if (path.includes('/usecase')) {
      if (selectedSecondaryCategory) {
        setSelectedKey(`usecase-${selectedSecondaryCategory}`);
      } else {
        setSelectedKey('usecase-use_cases');
      }
    } else if (path.includes('/chat')) {
      setSelectedKey('1');
    } else if (path.includes('/agent') || path.includes('/orchestration')) {
      setSelectedKey('2');
    } else if (path.includes('/mcp')) {
      setSelectedKey('3');
    } else if (path.includes('/restapi')) {
      setSelectedKey('7');
    } else if (path.includes('/schedule')) {
      setSelectedKey('4');
    } else if (path.includes('/user-management')) {
      setSelectedKey('6');
    } else if (path.includes('/config')) {
      setSelectedKey('5');
    }
  }, [selectedSecondaryCategory]);

  const handleLogout = async () => {
    try {
      await userAPI.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local state
      logout();
      
      // If user logged in via Azure AD, also logout from Azure AD
      if (user?.auth_provider === 'azure_ad') {
        await instance.logoutRedirect({
          postLogoutRedirectUri: window.location.origin
        });
      } else {
        // For regular users, just navigate to login
        navigate('/login');
      }
    }
  };

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'Profile',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Logout',
      onClick: handleLogout,
    },
  ];

  // Create use case menu items
  const useCaseMenuItems = primaryCategories.map(category => ({
    key: `usecase-${category.key}`,
    icon: <AppstoreOutlined />,
    label: category.key_display_name,
    children: secondaryCategories.map(subCategory => ({
      key: `usecase-${subCategory.key}`,
      label: subCategory.key_display_name,
      onClick: () => handleUseCaseMenuClick(subCategory.key, [category.key, subCategory.key])
    }))
  }));

  // Create menu items with conditional admin items
  const baseMenuItems = [
    // Use case menu items (above Agent Chatbot)
    ...useCaseMenuItems,
    {
      type: 'divider' as const,
    },
    {
      key: '1',
      icon: <CommentOutlined />,
      label: <Link to="/chat">Agent Chatbot</Link>,
    },
    {
      key: '2',
      icon: <SettingOutlined />,
      label: <Link to="/agent">Agent 管理</Link>,
    },
    {
      key: '3',
      icon: <AppstoreOutlined />,
      label: <Link to="/mcp">MCP 列表</Link>,
    },
    {
      key: '7',
      icon: <ApiOutlined />,
      label: <Link to="/restapi">REST API</Link>,
    },
    {
      key: '4',
      icon: <ScheduleOutlined />,
      label: <Link to="/schedule">Agent 调度</Link>,
    },
  ];

  // Add admin-only menu items
  const adminMenuItems = user?.is_admin ? [
    {
      type: 'divider' as const,
    },
    {
      key: '6',
      icon: <UserOutlined />,
      label: <Link to="/user-management">用户管理</Link>,
    },
    {
      key: '5',
      icon: <ControlOutlined />,
      label: <Link to="/config">系统配置</Link>,
    },
  ] : [
    // {
    //   key: '5',
    //   icon: <ControlOutlined />,
    //   label: <Link to="/config">系统配置</Link>,
    // },
  ];

  const menuItems = [...baseMenuItems, ...adminMenuItems];

  return (
    <ProtectedRoute>
      <AntLayout style={{ minHeight: '100vh' }}>
        <Sider 
          collapsible 
          collapsed={collapsed} 
          onCollapse={setCollapsed}
          trigger={null}
          theme="light"
          style={{ 
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
            zIndex: 10
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', padding: '16px 0' }}>
            <div 
              style={{ 
                padding: '0 16px',
                cursor: 'pointer',
                fontSize: '16px'
              }}
              onClick={() => setCollapsed(!collapsed)}
            >
              {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            </div>
            {!collapsed && <span style={{ fontWeight: 'bold' }}>Agent X</span>}
          </div>
          <Menu
            theme="light"
            mode="inline"
            selectedKeys={[selectedKey]}
            items={menuItems}
            // defaultOpenKeys={["usecase-use_cases"]}
            onClick={e => {
              setSelectedKey(e.key);
              // Clear use case selection when clicking non-use case menu items
              if (!e.key.startsWith('usecase-')) {
                setSelectedPrimaryCategory(null);
                setSelectedSecondaryCategory(null);
              }
            }}
          />
          
          {/* User info at bottom */}
          {isAuthenticated && user && (
            <div style={{ 
              position: 'absolute', 
              bottom: '16px', 
              left: '16px', 
              right: '16px',
              borderTop: '1px solid #f0f0f0',
              paddingTop: '16px'
            }}>
              {!collapsed ? (
                <Dropdown menu={{ items: userMenuItems }} placement="topLeft">
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    cursor: 'pointer',
                    padding: '8px',
                    borderRadius: '6px',
                    transition: 'background-color 0.3s',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f5f5f5'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    <Avatar size="small" icon={<UserOutlined />} />
                    <span style={{ marginLeft: '8px', fontSize: '14px' }}>
                      {user.username}
                    </span>
                  </div>
                </Dropdown>
              ) : (
                <Dropdown menu={{ items: userMenuItems }} placement="topRight">
                  <Avatar size="small" icon={<UserOutlined />} style={{ cursor: 'pointer' }} />
                </Dropdown>
              )}
            </div>
          )}
        </Sider>
        <Content style={{ background: '#fff' }}>
          <Routes>
            <Route path="/usecase" element={<UseCase />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/chat-detail" element={<ChatDetail />} />
            <Route path="/agent" element={<AgentHub />} />
            <Route path="/mcp" element={<MCP />} />
            <Route path="/restapi" element={<RestAPI />} />
            <Route path="/schedule" element={<Schedule />} />
            <Route path="/config" element={<Config />} />
            <Route path="/user-management" element={<UserManagement />} />
            <Route path="/orchestration" element={<AgentHub />} />
            <Route path="/orchestration/create" element={<OrchestrationEditor />} />
            <Route path="/orchestration/edit/:id" element={<OrchestrationEditor />} />
            <Route path="/" element={<Navigate to="/chat" replace />} />
          </Routes>
        </Content>
      </AntLayout>
    </ProtectedRoute>
  );
};

export const Layout: React.FC = () => {
  return (
    <Router>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        
        {/* Protected routes */}
        <Route path="/*" element={<LayoutContent />} />
      </Routes>
    </Router>
  );
};
