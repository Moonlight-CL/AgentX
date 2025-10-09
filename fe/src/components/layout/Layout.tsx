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
  ControlOutlined
} from '@ant-design/icons';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import { Chat } from '../chat/Chat';
import { AgentHub } from '../agent';
import { MCP } from '../mcp/MCP';
import { Schedule } from '../schedule';
import { Config } from '../config/Config';
import { OrchestrationEditor } from '../orchestration';
import { Login, Register, ProtectedRoute } from '../auth';
import { useUserStore } from '../../store/userStore';
import { userAPI } from '../../services/api';

const { Sider, Content } = AntLayout;

export const Layout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [selectedKey, setSelectedKey] = useState('1');
  const { isAuthenticated, user, logout } = useUserStore();

  // Update selected key based on current path
  useEffect(() => {
    const path = window.location.pathname;
    if (path.includes('/chat')) {
      setSelectedKey('1');
    } else if (path.includes('/agent') || path.includes('/orchestration')) {
      setSelectedKey('2');
    } else if (path.includes('/mcp')) {
      setSelectedKey('3');
    } else if (path.includes('/schedule')) {
      setSelectedKey('4');
    } else if (path.includes('/config')) {
      setSelectedKey('5');
    }
  }, []);

  const handleLogout = async () => {
    try {
      await userAPI.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      logout();
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

  const menuItems = [
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
      key: '4',
      icon: <ScheduleOutlined />,
      label: <Link to="/schedule">Agent 调度</Link>,
    },
    {
      key: '5',
      icon: <ControlOutlined />,
      label: <Link to="/config">系统配置</Link>,
    },
  ];

  return (
    <Router>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        
        {/* Protected routes */}
        <Route path="/*" element={
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
                  onClick={e => setSelectedKey(e.key)}
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
                  <Route path="/chat" element={<Chat />} />
                  <Route path="/agent" element={<AgentHub />} />
                  <Route path="/mcp" element={<MCP />} />
                  <Route path="/schedule" element={<Schedule />} />
                  <Route path="/config" element={<Config />} />
                  <Route path="/orchestration" element={<AgentHub />} />
                  <Route path="/orchestration/create" element={<OrchestrationEditor />} />
                  <Route path="/orchestration/edit/:id" element={<OrchestrationEditor />} />
                  <Route path="/" element={<Navigate to="/chat" replace />} />
                </Routes>
              </Content>
            </AntLayout>
          </ProtectedRoute>
        } />
      </Routes>
    </Router>
  );
};
