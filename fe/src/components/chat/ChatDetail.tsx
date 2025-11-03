import React from 'react';
import { Button } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useStyles } from '../../styles';
import { useAgent } from '../../hooks/useAgent';
import { useChatStore } from '../../store';
import { ChatList } from './ChatList';
import { ChatInput } from './ChatInput';

export const ChatDetail: React.FC = () => {
  const { styles } = useStyles();
  const { loading, handleSubmit, handleAbort, setXChatMessages} = useAgent();
  const navigate = useNavigate();
  
  // Fetch conversations and agents when component mounts
  React.useEffect(() => {
    const { fetchConversations, fetchAgents } = useChatStore.getState();
    fetchConversations();
    fetchAgents();
  }, []);

  const handleBack = () => {
    navigate(-1); // Go back to previous page
  };

  return (
    <div className={styles.chat} style={{ height: '100vh', overflow: 'hidden' }}>
      {/* Back button header */}
      <div style={{ 
        padding: '16px 24px', 
        borderBottom: '1px solid #f0f0f0',
        backgroundColor: '#fff',
        display: 'flex',
        alignItems: 'center',
        gap: '12px'
      }}>
        <Button 
          type="text" 
          icon={<ArrowLeftOutlined />}
          onClick={handleBack}
          style={{ 
            display: 'flex',
            alignItems: 'center',
            padding: '4px 8px'
          }}
        >
          返回
        </Button>
        <span style={{ 
          fontSize: '16px', 
          fontWeight: 500,
          color: '#262626'
        }}>
          对话详情
        </span>
      </div>
      
      {/* Chat content */}
      <div style={{ height: 'calc(100vh - 73px)', overflow: 'auto' }}>
        <ChatList onSubmit={handleSubmit} />
        <ChatInput onSubmit={handleSubmit} onCancel={handleAbort} loading={loading} setXChatMessages={setXChatMessages}/>
      </div>
    </div>
  );
};
