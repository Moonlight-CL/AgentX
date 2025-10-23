import React from 'react';
import { Card, Tag, Typography, Space } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import type { UseCaseItem } from '../../store/useCaseStore';

const { Text, Paragraph } = Typography;

interface UseCaseCardProps {
  item: UseCaseItem;
  onClick: (item: UseCaseItem) => void;
}

export const UseCaseCard: React.FC<UseCaseCardProps> = ({ item, onClick }) => {
  const handleClick = () => {
    onClick(item);
  };

  return (
    <Card
      hoverable
      onClick={handleClick}
      style={{ 
        marginBottom: 16,
        cursor: 'pointer',
        borderRadius: 8,
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)'
      }}
      styles={{ body: {padding: 16}}}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* Header with title and play icon */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Text strong style={{ fontSize: 16, color: '#1890ff' }}>
            {item.key_display_name}
          </Text>
          <PlayCircleOutlined 
            style={{ 
              fontSize: 20, 
              color: '#52c41a',
              opacity: 0.7
            }} 
          />
        </div>

        {/* Tags */}
        {item.tags && item.tags.length > 0 && (
          <Space wrap>
            {item.tags.map((tag, index) => (
              <Tag 
                key={index} 
                color="blue"
                style={{ borderRadius: 4 }}
              >
                {tag}
              </Tag>
            ))}
          </Space>
        )}

        {/* Description */}
        {item.desc && (
          <Paragraph 
            ellipsis={{ rows: 2, expandable: false }}
            style={{ 
              margin: 0, 
              color: '#666',
              fontSize: 14,
              lineHeight: 1.5
            }}
          >
            {item.desc}
          </Paragraph>
        )}

        {/* Record ID (if available) */}
        {item.record_id && (
          <Text 
            type="secondary" 
            style={{ 
              fontSize: 12,
              fontFamily: 'monospace'
            }}
          >
            记录ID: {item.record_id}
          </Text>
        )}
      </div>
    </Card>
  );
};
