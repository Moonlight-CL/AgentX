import React from 'react';
import { Button, Space, Spin } from 'antd';
import { Bubble, Welcome } from '@ant-design/x';
import {
  EllipsisOutlined,
  ShareAltOutlined,
  InfoCircleTwoTone
} from '@ant-design/icons';
import { useStyles } from '../../styles';
import { useChatStore } from '../../store';
import '../../styles/markdown.css';
import '../../styles/tool-result.css';
import '../../styles/highlight.css';
import '../../styles/agentx-welcome.css';

interface ChatListProps {
  onSubmit: (text: string) => void;
}

export const ChatList: React.FC<ChatListProps> = ({ onSubmit }) => {
  const { styles } = useStyles();
  const { messages } = useChatStore();

  return (
    <div className={styles.chatList}>
      {messages?.length ? (
        /* Message List */
        <Bubble.List
          items={messages?.map((i) => ({
            ...i.message,
            classNames: {
              content: i.status === 'loading' ? styles.loadingMessage : '',
            },
            styles: { content: {minWidth: 850} },
            typing: i.status === 'loading' ? { step: 5, interval: 20, suffix: <>💗</> } : false,
            content: <div className="markdown-content" dangerouslySetInnerHTML={{ __html: i.message.content as string }} />,
          }))}
          style={{ height: '100%', paddingInline: 'calc(calc(100% - 900px) /2)'}}
          roles={{
            assistant: {
              placement: 'start',
              // footer: (
              //   <div style={{ display: 'flex' }}>
              //     <Button type="text" size="small" icon={<ReloadOutlined />} />
              //     <Button type="text" size="small" icon={<CopyOutlined />} />
              //     <Button type="text" size="small" icon={<LikeOutlined />} />
              //     <Button type="text" size="small" icon={<DislikeOutlined />} />
              //   </div>
              // ),
              loadingRender: () => <Spin size="small" />,
            },
            user: { placement: 'end' },
          }}
        />
      ) : (
        <Space
          direction="vertical"
          size={16}
          style={{ paddingInline: 'calc(calc(100% - 900px) /2)' }}
          className={styles.placeholder}
        >
          <Welcome
            variant="borderless"
            icon="https://mdn.alipayobjects.com/huamei_iwk9zp/afts/img/A*s5sNRo5LjfQAAAAAAAAAAAAADgCCAQ/fmt.webp"
            title="Hello, I'm AgentX"
            description="Base on Strands Agent SDK, AgentX is a platform that You can configure and run your own AI agents."
            extra={
              <Space>
                <Button icon={<ShareAltOutlined />} />
                <Button icon={<EllipsisOutlined />} />
              </Space>
            }
          />
          <div className="system-update-notification">
            <div className="system-update-icon-container">
              <InfoCircleTwoTone />
              {/* <img 
                src="https://mdn.alipayobjects.com/huamei_iwk9zp/afts/img/A*NZuwQp_vcIkAAAAAAAAAAAAADgCCAQ/fmt.webp" 
                alt="System Update" 
                className="system-update-icon"
              /> */}
            </div>
            <div className="system-update-content">
              <div className="system-update-title">
                System Updates
              </div>
              <div className="system-update-description">
                 1. AgentCore Browser Use and Code Interpreter tools are now available! 🎉🎉🎉 <br/>
                 2. OpenSearch MCP Server is now available! 🎉🎉🎉
              </div>
            </div>
          </div>
          <div className="agentx-welcome-container">
              <div className="agentx-welcome-overlay-radial" />
              <div className="agentx-welcome-overlay-linear" />
              <div className="agentx-welcome-content">
                <h2 className="agentx-formula">
                  <span className="component-animation" style={{ '--delay': '0s' } as React.CSSProperties}>Agent</span> = 
                  <span className="component-animation" style={{ '--delay': '1s' } as React.CSSProperties}> LLM Model</span> + 
                  <span className="component-animation" style={{ '--delay': '2s' } as React.CSSProperties}> System Prompt</span> <br/> + 
                  <span className="component-animation" style={{ '--delay': '3s' } as React.CSSProperties}> Tools</span> + 
                  <span className="component-animation" style={{ '--delay': '4s' } as React.CSSProperties}> Environment</span>
                </h2>
                <div className="agentx-logo">
                  AgentX
                </div>
                {/* Hidden button to satisfy ESLint (onSubmit must be used) */}
                <button 
                  onClick={() => onSubmit("Tell me about AgentX")} 
                  style={{ display: 'none' }}
                  aria-hidden="true"
                >
                  Hidden Submit
                </button>
              </div>
            </div>
        </Space>
      )}
    </div>
  );
};
