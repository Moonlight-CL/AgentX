import React, { useEffect, useState } from 'react';
import { Flex, Space, Typography, Switch, Divider, message } from 'antd';
import { Sender, Suggestion, Attachments } from '@ant-design/x';
import { UserOutlined, PaperClipOutlined } from '@ant-design/icons';
import { useStyles } from '../../styles';
import { useChatStore } from '../../store';
import type { Agent } from '../../services/api';
import { fileAPI } from '../../services/api';

interface ChatInputProps {
  onSubmit: (text: string, fileattachments?: any[]) => void;
  onCancel: () => void;
  loading: boolean;
  setXChatMessages: (action: []) => void
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSubmit, onCancel, loading, setXChatMessages}) => {
  const { styles } = useStyles();
  const { 
    inputValue, 
    setInputValue, 
    agents, 
    selectedAgent, 
    chatRecordEnabled,
    setSelectedAgent, 
    setChatRecordEnabled,
    fetchAgents,
    setMessages,
    setCurrentChatId,
    setAgentEvents
  } = useChatStore();
  
  // File attachment state
  const [fileList, setFileList] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  
  // Fetch agents when component mounts
  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const handleSubmit = async () => {
    if (!inputValue && fileList.length === 0) return;
    
    // Check if agent is selected
    if (!selectedAgent) {
      message.warning('Please select an agent first');
      return;
    }
    
    // Upload files if any
    let uploadedFiles: any[] = [];
    if (fileList.length > 0) {
      try {
        setUploading(true);
        const filesToUpload = fileList.map(file => file.originFileObj);
        const result = await fileAPI.uploadFiles(filesToUpload);
        uploadedFiles = result.files;
      } catch (error) {
        // message.error(`Failed to upload files`);
        if (typeof error === 'string') {
          message.error(error);
        } else if (error instanceof Error) {
          message.error(error.message);
        } else if (typeof error === 'object' && error !== null && 'message' in error && typeof (error as any).message === 'string') {
          message.error((error as any).message);
        } else {
          message.error('Failed to upload files');
        }
        return;
      } finally {
        setUploading(false);
      }
    }
    onSubmit(inputValue, uploadedFiles);
    setInputValue('');
    setFileList([]);
  };
  
  // Handle agent selection from suggestion
  const handleAgentSelect = (agent: Agent) => {
    setSelectedAgent(agent);
    //when user select a new Agent, init a new session
    setInputValue("");
    setMessages([]);
    setAgentEvents([]);
    setCurrentChatId(null);
    setXChatMessages([]);
  };

  return (
    <div className={styles.sender}>
        {/* Input with Suggestion */}
        <Suggestion
          items={agents.map(agent => ({
            key: agent.id,
            label: agent.display_name,
            description: agent.description,
            value: agent.display_name,
            data: agent
          }))}
          onSelect={(value: string) => {
            // Find the agent by display name
            const agent = agents.find(a => a.display_name === value);
            if (agent) {
              handleAgentSelect(agent);
            }
          }}
        >
          {({ onTrigger, onKeyDown }) => (
            <Sender
              value={inputValue}
              autoSize={{ minRows: 3, maxRows: 6 }}
              header={
                selectedAgent && (
                  <Sender.Header
                    open={!!selectedAgent}
                    title={
                      <Space>
                        <UserOutlined />
                        <Typography.Text type="secondary">您已选择 [{selectedAgent.display_name}]</Typography.Text>
                      </Space>
                    }
                    onOpenChange={(open) => {
                      console.log(`onOpenChange: ${open}`);
                      if (!open) {
                        
                        setSelectedAgent(null);
                        setInputValue('');
                      }
                    }}
                  />
                )
              }
              onSubmit={handleSubmit}
              onChange={(value) => {
                if (value === '/') {
                  console.log(`sender onChange: value: ${value}`);
                  onTrigger();
                } else if (!value) {
                  onTrigger(false);
                }
                setInputValue(value);
              }}
              onKeyDown={onKeyDown}
              onCancel={onCancel}
              loading={loading}
              className={styles.sender}
              allowSpeech
              footer={({ components }) => {
                const { SendButton, LoadingButton, SpeechButton } = components;
                return (
                  <div>
                    {/* File attachments */}
                    {fileList.length > 0 && (
                      <div style={{ marginBottom: 8 }}>
                        <Attachments
                          items={fileList.map(file => ({
                            uid: file.uid,
                            name: file.name,
                            status: uploading ? 'uploading' : 'done',
                          }))}
                          onRemove={(item) => {
                            setFileList(prev => prev.filter(file => file.uid !== item.uid));
                          }}
                        />
                      </div>
                    )}
                    <Flex justify="space-between" align="center">
                      <Flex gap="small" align="center">
                        <Space>
                          <Attachments
                            beforeUpload={(file) => {
                              const isLt2M = file.size / 1024 / 1024 < 10;
                              if (!isLt2M) {
                                message.error('文件必须小于2MB!');
                                return false;
                              }
                              // Add file to list without uploading immediately
                              const newFile = {
                                uid: Date.now().toString(),
                                name: file.name,
                                status: 'done',
                                originFileObj: file,
                              };
                              setFileList(prev => [...prev, newFile]);
                              return false; // Prevent automatic upload
                            }}
                            showUploadList={false}
                            multiple
                            accept="image/*,video/*,.pdf,.doc,.docx,.txt,.csv,.xls,.xlsx,.html,.md"
                          >
                            <PaperClipOutlined style={{ cursor: 'pointer', fontSize: 16 }} />
                          </Attachments>
                          <Divider type="vertical" />
                          <UserOutlined />
                          Chat History
                          <Switch 
                            size="small" 
                            checked={chatRecordEnabled}
                            onChange={(checked) => {
                              setChatRecordEnabled(checked);
                            }}
                          />
                        </Space>
                      </Flex>
                      <Flex align="center">
                        
                        <SpeechButton className={styles.speechButton} />
                        <Divider type="vertical" />
                        {loading || uploading ? <LoadingButton type="default" /> : <SendButton type="primary" />}
                      </Flex>
                    </Flex>
                  </div>
                );
              }}
              actions={false}
              placeholder="Ask or input / to select an agent"
            />
          )}
        </Suggestion>
      </div>
  );
};
