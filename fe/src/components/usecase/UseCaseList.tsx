import React from 'react';
import { Row, Col, Spin, Empty, Alert } from 'antd';
import { useNavigate } from 'react-router-dom';
import { UseCaseCard } from './UseCaseCard';
import { useUseCaseStore } from '../../store/useCaseStore';
import { useChatStore } from '../../store';
import type { UseCaseItem } from '../../store/useCaseStore';

export const UseCaseList: React.FC = () => {
  const navigate = useNavigate();
  const { 
    useCaseItems, 
    loading, 
    error,
    selectedSecondaryCategory 
  } = useUseCaseStore();
  
  const { loadChatResponses } = useChatStore();

  const handleCardClick = async (item: UseCaseItem) => {
    if (item.record_id) {
      // Load the conversation data
      await loadChatResponses(item.record_id);
      // Navigate to chat detail page to show the conversation (without sidebar)
      navigate('/chat-detail');
    }
  };

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '400px' 
      }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        message="加载失败"
        description={error}
        type="error"
        showIcon
        style={{ margin: '20px 0' }}
      />
    );
  }

  if (!selectedSecondaryCategory) {
    return (
      <Empty
        description="请选择一个应用分类查看相关案例"
        style={{ margin: '40px 0' }}
      />
    );
  }

  if (useCaseItems.length === 0) {
    return (
      <Empty
        description="该分类下暂无应用案例"
        style={{ margin: '40px 0' }}
      />
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      <Row gutter={[16, 16]}>
        {useCaseItems.map((item) => (
          <Col xs={24} sm={12} md={8} lg={6} key={item.key}>
            <UseCaseCard 
              item={item} 
              onClick={handleCardClick}
            />
          </Col>
        ))}
      </Row>
    </div>
  );
};
