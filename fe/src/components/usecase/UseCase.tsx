import React, { useEffect } from 'react';
import { Typography, Breadcrumb } from 'antd';
import { HomeOutlined, AppstoreOutlined } from '@ant-design/icons';
import { useUseCaseStore } from '../../store/useCaseStore';
import { UseCaseList } from './UseCaseList';

const { Title } = Typography;

export const UseCase: React.FC = () => {
  const { 
    selectedPrimaryCategory,
    selectedSecondaryCategory,
    primaryCategories,
    secondaryCategories,
    fetchPrimaryCategories,
    fetchSecondaryCategories
  } = useUseCaseStore();

  // Fetch categories when component mounts
  useEffect(() => {
    if (primaryCategories.length === 0) {
      fetchPrimaryCategories();
    }
  }, [primaryCategories.length, fetchPrimaryCategories]);

  // Fetch secondary categories when primary category is selected
  useEffect(() => {
    if (selectedPrimaryCategory && secondaryCategories.length === 0) {
      fetchSecondaryCategories(selectedPrimaryCategory);
    }
  }, [selectedPrimaryCategory, secondaryCategories.length, fetchSecondaryCategories]);

  // Get display names for breadcrumb
  const primaryCategoryName = primaryCategories.find(cat => cat.key === selectedPrimaryCategory)?.key_display_name || 'Agent应用';
  const secondaryCategoryName = secondaryCategories.find(cat => cat.key === selectedSecondaryCategory)?.key_display_name || '';

  return (
    <div style={{ 
      padding: '24px',
      minHeight: '100vh',
      backgroundColor: '#f5f5f5'
    }}>
      {/* Breadcrumb */}
      <Breadcrumb style={{ marginBottom: '24px' }}>
        <Breadcrumb.Item href="/">
          <HomeOutlined />
        </Breadcrumb.Item>
        <Breadcrumb.Item>
          <AppstoreOutlined />
          <span>{primaryCategoryName}</span>
        </Breadcrumb.Item>
        {secondaryCategoryName && (
          <Breadcrumb.Item>{secondaryCategoryName}</Breadcrumb.Item>
        )}
      </Breadcrumb>

      {/* Title */}
      <div style={{ 
        backgroundColor: '#fff',
        padding: '24px',
        borderRadius: '8px',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
        marginBottom: '24px'
      }}>
        <Title level={2} style={{ margin: 0 }}>
          {secondaryCategoryName ? `${secondaryCategoryName} - 应用案例` : 'Agent 应用案例'}
        </Title>
        {secondaryCategoryName && (
          <p style={{ 
            color: '#666', 
            fontSize: '16px', 
            marginTop: '8px',
            marginBottom: 0
          }}>
            浏览 {secondaryCategoryName} 相关的 Agent 应用案例，点击卡片查看详细对话记录
          </p>
        )}
      </div>

      {/* Use Case List */}
      <div style={{ 
        backgroundColor: '#fff',
        borderRadius: '8px',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
        minHeight: '400px'
      }}>
        <UseCaseList />
      </div>
    </div>
  );
};
