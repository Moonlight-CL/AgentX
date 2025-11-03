import React from 'react';
import { Avatar, Button, message } from 'antd';
import { Conversations } from '@ant-design/x';
import { DeleteOutlined, EditOutlined, PlusOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import { useStyles } from '../../styles';
import { useChatStore } from '../../store';
import { useAgent } from '../../hooks/useAgent';

export const Sidebar: React.FC = () => {
  const { styles } = useStyles();
  const { 
    conversations, 
    createNewConversation, 
    deleteConversation, 
    setSelectedAgent,
    currentChatId,
    loadChatResponses
  } = useChatStore();
  const { loading, handleAbort, setXChatMessages} = useAgent();
  
  // Fetch conversations when component mounts
  React.useEffect(() => {
    const { fetchConversations } = useChatStore.getState();
    fetchConversations();
  }, []);

  return (
    <div className={styles.sider}>
      {/* Logo */}
      <div className={styles.logo}>
        <img
          src="https://mdn.alipayobjects.com/huamei_iwk9zp/afts/img/A*s5sNRo5LjfQAAAAAAAAAAAAADgCCAQ/fmt.webp"
          draggable={false}
          alt="logo"
          width={24}
          height={24}
        />
        <span>AgentX</span>
      </div>

      {/* Add Conversation Button */}
      <Button
        onClick={() => {
          if (loading) {
            console.error(
              'Message is Requesting, you can create a new conversation after request done or abort it right now...',
            );
            return;
          }

          handleAbort();
          setSelectedAgent(null);
          setXChatMessages([]);
          createNewConversation();
        }}
        type="link"
        className={styles.addBtn}
        icon={<PlusOutlined />}
      >
        New Conversation
      </Button>

      {/* Conversation Management */}
      <Conversations
        items={conversations}
        className={styles.conversations}
        activeKey={currentChatId || ''}
        onActiveChange={async (val) => {
          handleAbort();
          // Load the chat responses for the selected conversation
          loadChatResponses(val);
        }}
        groupable
        styles={{ item: { padding: '0 8px' } }}
        menu={(conversation) => ({
          items: [
            {
              label: 'Rename',
              key: 'rename',
              icon: <EditOutlined />,
            },
            {
              label: 'Delete',
              key: 'delete',
              icon: <DeleteOutlined />,
              danger: true,
              onClick: async () => {
                try {
                  // Call the deleteConversation function with the conversation key
                  // console.log(conversation.key);
                  const result = await deleteConversation(conversation.key);
                  
                  if (result.success) {
                    setXChatMessages([]);
                    message.success(result.message);
                  } else {
                    message.error(result.message);
                  }
                } catch (error) {
                  console.error('Error deleting conversation:', error);
                  message.error('删除对话时发生未知错误');
                }
              },
            },
          ],
        })}
      />

      <div className={styles.siderFooter}>
        <Avatar size={24} />
        <Button type="text" icon={<QuestionCircleOutlined />} />
      </div>
    </div>
  );
};
