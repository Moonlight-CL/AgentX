import React, { useState, useEffect } from 'react';
import { Tabs } from 'antd';
import { SettingOutlined, ApartmentOutlined } from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import { AgentManager } from './Agent';
import { OrchestrationManager } from '../orchestration';

// const { TabPane } = Tabs;

export const AgentHub: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('agent');

  // Set active tab based on current path
  useEffect(() => {
    if (location.pathname.includes('/orchestration')) {
      setActiveTab('multi-agent');
    } else {
      setActiveTab('agent');
    }
  }, [location.pathname]);

  const handleTabChange = (key: string) => {
    setActiveTab(key);
    // Update URL based on tab selection
    if (key === 'multi-agent') {
      navigate('/orchestration');
    } else {
      navigate('/agent');
    }
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Tabs
        activeKey={activeTab}
        onChange={handleTabChange}
        style={{ height: '100%' }}
        tabBarStyle={{ 
          margin: 0, 
          paddingLeft: '24px',
          paddingRight: '24px',
          borderBottom: '1px solid #f0f0f0'
        }}
        items={[
          {
            key: 'agent',
            label: (
              <span>
                <SettingOutlined />
                Agent
              </span>
            ),
            children: <AgentManager />,
          },
          {
            key: 'multi-agent',
            label: (
              <span>
                <ApartmentOutlined />
                Multi-Agent
              </span>
            ),
            children: <OrchestrationManager />,
          },
        ]}
      />
    </div>
  );
};
