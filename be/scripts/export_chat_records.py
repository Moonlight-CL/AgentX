#!/usr/bin/env python3
"""
ChatRecordTable数据导出脚本
将现有的ChatRecordTable数据导出为JSON格式，为表结构重建做准备
"""

import json
import boto3
from datetime import datetime
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.utils.aws_config import get_aws_region, DynamoDBTables

def export_chat_records():
    """导出ChatRecordTable中的所有数据"""
    
    # 初始化DynamoDB资源
    aws_region = get_aws_region()
    dynamodb = boto3.resource('dynamodb', region_name=aws_region)
    
    # 获取表
    chat_record_table = dynamodb.Table(DynamoDBTables.CHAT_RECORDS)
    chat_response_table = dynamodb.Table(DynamoDBTables.CHAT_RESPONSES)
    
    print(f"开始导出ChatRecordTable数据...")
    print(f"AWS Region: {aws_region}")
    print(f"ChatRecord表名: {DynamoDBTables.CHAT_RECORDS}")
    print(f"ChatResponse表名: {DynamoDBTables.CHAT_RESPONSES}")
    
    # 导出ChatRecord数据
    chat_records = []
    try:
        # 扫描整个表
        response = chat_record_table.scan()
        chat_records.extend(response['Items'])
        
        # 处理分页
        while 'LastEvaluatedKey' in response:
            response = chat_record_table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            chat_records.extend(response['Items'])
        
        print(f"成功导出 {len(chat_records)} 条ChatRecord记录")
        
    except Exception as e:
        print(f"导出ChatRecord数据时出错: {str(e)}")
        return False
    
    # 数据预处理：处理user_id为空的情况
    processed_records = []
    for record in chat_records:
        # 如果user_id为空或不存在，设置为'public'
        if not record.get('user_id') or record.get('user_id').strip() == '':
            record['user_id'] = 'public'
        processed_records.append(record)
    
    # 创建导出数据结构
    export_data = {
        'export_timestamp': datetime.now().isoformat(),
        'aws_region': aws_region,
        'chat_records': processed_records,
        'statistics': {
            'chat_records_count': len(processed_records),
            'public_records_count': len([r for r in processed_records if r.get('user_id') == 'public'])
        }
    }
    
    # 保存到JSON文件
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'chat_records_backup_{timestamp}.json'
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n✅ 数据导出成功!")
        print(f"📁 文件名: {filename}")
        print(f"📊 统计信息:")
        print(f"   - ChatRecord记录数: {export_data['statistics']['chat_records_count']}")
        print(f"   - Public记录数: {export_data['statistics']['public_records_count']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 保存文件时出错: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("ChatRecordTable 数据导出工具")
    print("=" * 60)
    
    success = export_chat_records()
    
    if success:
        print("\n🎉 导出完成! 请检查生成的JSON文件。")
    else:
        print("\n❌ 导出失败! 请检查错误信息。")
        sys.exit(1)
