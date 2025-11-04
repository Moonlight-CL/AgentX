import React, { useState, useEffect, useRef } from 'react';
import { 
  Card, 
  Form, 
  Input, 
  Button, 
  Space, 
  Divider,
  Tag, 
  Alert,
  Typography,
  Switch
} from 'antd';
import { PlayCircleOutlined, StopOutlined, ReloadOutlined } from '@ant-design/icons';
import { useOrchestrationStore } from '../../store/orchestrationStore';

const { TextArea } = Input;
const { Text } = Typography;

export const OrchestrationExecution: React.FC = () => {
  const [form] = Form.useForm();
  const [executing, setExecuting] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const intervalRef = useRef<number | null>(null);
  
  const {
    currentOrchestration,
    currentExecution,
    executionLoading,
    executeOrchestration,
    stopExecution,
    getExecutionStatus,
  } = useOrchestrationStore();

  // Auto-refresh effect
  useEffect(() => {
    // Clear existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    // Only start auto-refresh if we have an execution and it's in a running state
    if (autoRefresh && currentExecution && 
        (currentExecution.status === 'running' || currentExecution.status === 'pending')) {
      intervalRef.current = setInterval(() => {
        if (currentExecution) {
          getExecutionStatus(currentExecution.id);
        }
      }, 10000); // 10 seconds
    }

    // Cleanup on unmount or when dependencies change
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [autoRefresh, currentExecution?.id, currentExecution?.status, getExecutionStatus]);

  // Stop auto-refresh when execution completes or fails
  useEffect(() => {
    if (currentExecution && 
        (currentExecution.status === 'completed' || currentExecution.status === 'failed')) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  }, [currentExecution?.status]);

  const handleExecute = async (values: { inputMessage: string; chatRecordEnabled?: boolean }) => {
    if (!currentOrchestration) return;
    
    setExecuting(true);
    try {
      await executeOrchestration(currentOrchestration.id, {
        inputMessage: values.inputMessage,
        chatRecordEnabled: values.chatRecordEnabled ?? true
      });
    } catch (error) {
      console.error('Execution failed:', error);
    } finally {
      setExecuting(false);
    }
  };

  const handleStop = async () => {
    if (currentExecution) {
      await stopExecution(currentExecution.id);
    }
  };

  const handleRefreshStatus = async () => {
    if (currentExecution) {
      await getExecutionStatus(currentExecution.id);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'orange';
      case 'running': return 'blue';
      case 'completed': return 'green';
      case 'failed': return 'red';
      default: return 'default';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending': return '等待中';
      case 'running': return '执行中';
      case 'completed': return '已完成';
      case 'failed': return '执行失败';
      default: return status;
    }
  };

  const renderExecutionProgress = () => {
    if (!currentExecution) return null;

    const { status} = currentExecution;
    // const totalNodes = currentOrchestration?.nodes.length || 0;
    // const completedNodes = nodeHistory.filter(node => node.status === 'completed').length;
    // const progressPercent = totalNodes > 0 ? (completedNodes / totalNodes) * 100 : 0;

    return (
      <Card title="执行进度" size="small" style={{ marginTop: '16px' }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text>状态: <Tag color={getStatusColor(status)}>{getStatusText(status)}</Tag></Text>
            <Space>
              <div style={{ display: 'flex', alignItems: 'center', fontSize: '12px' }}>
                <Text style={{ fontSize: '12px', marginRight: '8px' }}>自动刷新(10s)</Text>
                <Switch 
                  size="small" 
                  checked={autoRefresh} 
                  onChange={setAutoRefresh}
                />
              </div>
              <Button 
                size="small" 
                icon={<ReloadOutlined />} 
                onClick={handleRefreshStatus}
                loading={executionLoading}
              >
                刷新
              </Button>
            </Space>
          </div>
          
          {/* <Progress 
            percent={Math.round(progressPercent)} 
            status={status === 'failed' ? 'exception' : status === 'completed' ? 'success' : 'active'}
            format={() => `${completedNodes}/${totalNodes}`}
          /> */}

          {/* {nodeHistory.length > 0 && (
            <>
              <Divider />
              <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                <Timeline
                  items={nodeHistory.map((node, index) => ({
                    color: getStatusColor(node.status),
                    children: (
                      <div>
                        <div style={{ fontWeight: 500 }}>
                          节点: {currentOrchestration?.nodes.find(n => n.id === node.nodeId)?.displayName || node.nodeId}
                        </div>
                        <div style={{ fontSize: '12px', color: '#666' }}>
                          状态: {getStatusText(node.status)} | 
                          执行时间: {node.executionTime}ms
                        </div>
                        {node.result && (
                          <div style={{ 
                            fontSize: '12px', 
                            color: '#999', 
                            marginTop: '4px',
                            maxWidth: '400px',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }}>
                            结果: {typeof node.result === 'string' ? node.result : JSON.stringify(node.result)}
                          </div>
                        )}
                      </div>
                    )
                  }))}
                />
              </div>
            </>
          )} */}
        </Space>
      </Card>
    );
  };

  const renderExecutionResult = () => {
    if (!currentExecution || currentExecution.status !== 'completed') return null;

    return (
      <Card title="执行结果" size="small" style={{ marginTop: '16px' }}>
        <div style={{ 
          background: '#f5f5f5', 
          padding: '12px', 
          borderRadius: '4px',
          maxHeight: '200px',
          overflowY: 'auto'
        }}>
          <pre style={{ margin: 0, fontSize: '12px', whiteSpace: 'pre-wrap' }}>
            {currentExecution.results ? 
              JSON.stringify(currentExecution.results, null, 2) : 
              '暂无结果'
            }
          </pre>
        </div>
      </Card>
    );
  };

  const renderErrorMessage = () => {
    if (!currentExecution || !currentExecution.errorMessage) return null;

    return (
      <Alert
        message="执行错误"
        description={currentExecution.errorMessage}
        type="error"
        showIcon
        style={{ marginTop: '16px' }}
      />
    );
  };

  if (!currentOrchestration) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <Text type="secondary">请先选择要执行的编排</Text>
      </div>
    );
  }

  return (
    <div style={{ padding: '16px' }}>
      <Card title={`执行编排: ${currentOrchestration.displayName}`} size="small">
        <Form
          form={form}
          layout="vertical"
          onFinish={handleExecute}
          initialValues={{
            chatRecordEnabled: true
          }}
        >
          <Form.Item
            name="inputMessage"
            label="输入消息"
            rules={[{ required: true, message: '请输入要执行的任务描述' }]}
          >
            <TextArea 
              rows={4} 
              placeholder="请描述您希望编排执行的任务..."
              disabled={executing || (currentExecution?.status === 'running')}
            />
          </Form.Item>

          <Space>
            <Button 
              type="primary" 
              htmlType="submit" 
              icon={<PlayCircleOutlined />}
              loading={executing || executionLoading}
              disabled={currentExecution?.status === 'running'}
            >
              开始执行
            </Button>
            
            {currentExecution?.status === 'running' && (
              <Button 
                danger
                icon={<StopOutlined />}
                onClick={handleStop}
              >
                停止执行
              </Button>
            )}
          </Space>
        </Form>

        {/* Orchestration Info */}
        <Divider />
        <div style={{ fontSize: '12px', color: '#666' }}>
          <div>编排类型: <Tag>{currentOrchestration.type}</Tag></div>
          <div style={{ marginTop: '4px' }}>
            节点数: {currentOrchestration.nodes.length} | 
            连接数: {currentOrchestration.edges.length}
            {currentOrchestration.entryPoint && (
              <span> | 入口点: {
                currentOrchestration.nodes.find(n => n.id === currentOrchestration.entryPoint)?.displayName || 
                currentOrchestration.entryPoint
              }</span>
            )}
          </div>
        </div>
      </Card>

      {/* Execution Progress */}
      {renderExecutionProgress()}

      {/* Execution Result */}
      {renderExecutionResult()}

      {/* Error Message */}
      {renderErrorMessage()}
    </div>
  );
};
