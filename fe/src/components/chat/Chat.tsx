import React from 'react';
import { useStyles } from '../../styles';
import { useAgent } from '../../hooks/useAgent';
import { useChatStore } from '../../store';
import { ChatList } from './ChatList';
import { ChatInput } from './ChatInput';
import { Sidebar } from '../sidebar/Sidebar';

export const Chat: React.FC = () => {
  const { styles } = useStyles();
  const { loading, handleSubmit, handleAbort, setXChatMessages} = useAgent();
  
  // Fetch conversations and agents when component mounts
  React.useEffect(() => {
    const { fetchConversations, fetchAgents } = useChatStore.getState();
    fetchConversations();
    fetchAgents();
  }, []);

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar />
      <div className={styles.chat} style={{ flex: 1, height: '100vh', overflow: 'hidden' }}>
        <ChatList onSubmit={handleSubmit} />
        <ChatInput onSubmit={handleSubmit} onCancel={handleAbort} loading={loading} setXChatMessages={setXChatMessages} />
      </div>
    </div>
  );
};
