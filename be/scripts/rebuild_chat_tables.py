#!/usr/bin/env python3
"""
ChatRecordTable表重建脚本
删除旧的ChatRecordTable并创建新的表结构（partition key: user_id, sort key: id）
"""

import boto3
import time
from datetime import datetime
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.utils.aws_config import get_aws_region, DynamoDBTables

def wait_for_table_deletion(dynamodb, table_name, max_wait_time=300):
    """等待表删除完成"""
    print(f"等待表 {table_name} 删除完成...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            table = dynamodb.Table(table_name)
            table.load()
            print(".", end="", flush=True)
            time.sleep(5)
        except dynamodb.meta.client.exceptions.ResourceNotFoundException:
            print(f"\n✅ 表 {table_name} 已成功删除")
            return True
        except Exception as e:
            print(f"\n检查表状态时出错: {str(e)}")
            time.sleep(5)
    
    print(f"\n❌ 等待表删除超时 ({max_wait_time}秒)")
    return False

def wait_for_table_creation(dynamodb, table_name, max_wait_time=300):
    """等待表创建完成"""
    print(f"等待表 {table_name} 创建完成...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            table = dynamodb.Table(table_name)
            table.load()
            if table.table_status == 'ACTIVE':
                print(f"\n✅ 表 {table_name} 已成功创建并激活")
                return True
            print(".", end="", flush=True)
            time.sleep(5)
        except Exception as e:
            print(f"\n检查表状态时出错: {str(e)}")
            time.sleep(5)
    
    print(f"\n❌ 等待表创建超时 ({max_wait_time}秒)")
    return False

def rebuild_chat_tables():
    """重建ChatRecord和ChatResponse表"""
    
    # 初始化DynamoDB资源
    aws_region = get_aws_region()
    dynamodb = boto3.resource('dynamodb', region_name=aws_region)
    
    print(f"开始重建ChatRecord相关表...")
    print(f"AWS Region: {aws_region}")
    
    # 1. 删除旧的ChatRecordTable
    print(f"\n🗑️  删除旧的ChatRecordTable...")
    try:
        chat_record_table = dynamodb.Table(DynamoDBTables.CHAT_RECORDS)
        chat_record_table.delete()
        
        # 等待删除完成
        if not wait_for_table_deletion(dynamodb, DynamoDBTables.CHAT_RECORDS):
            return False
            
    except dynamodb.meta.client.exceptions.ResourceNotFoundException:
        print(f"表 {DynamoDBTables.CHAT_RECORDS} 不存在，跳过删除")
    except Exception as e:
        print(f"❌ 删除ChatRecordTable时出错: {str(e)}")
        return False
    
    # 2. 创建新的ChatRecordTable（partition key: user_id, sort key: id）
    print(f"\n🔨 创建新的ChatRecordTable...")
    try:
        new_chat_record_table = dynamodb.create_table(
            TableName=DynamoDBTables.CHAT_RECORDS,
            KeySchema=[
                {
                    'AttributeName': 'user_id',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'id',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # 按需付费模式
        )
        
        # 等待创建完成
        if not wait_for_table_creation(dynamodb, DynamoDBTables.CHAT_RECORDS):
            return False
            
    except Exception as e:
        print(f"❌ 创建新ChatRecordTable时出错: {str(e)}")
        return False
    
    # 3. 检查ChatResponseTable是否需要重建（如果不存在则创建）
    print(f"\n🔍 检查ChatResponseTable...")
    try:
        chat_response_table = dynamodb.Table(DynamoDBTables.CHAT_RESPONSES)
        chat_response_table.load()
        print(f"✅ ChatResponseTable已存在，无需重建")
    except dynamodb.meta.client.exceptions.ResourceNotFoundException:
        print(f"🔨 创建ChatResponseTable...")
        try:
            new_chat_response_table = dynamodb.create_table(
                TableName=DynamoDBTables.CHAT_RESPONSES,
                KeySchema=[
                    {
                        'AttributeName': 'id',
                        'KeyType': 'HASH'  # Partition key (chat_id)
                    },
                    {
                        'AttributeName': 'resp_no',
                        'KeyType': 'RANGE'  # Sort key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'id',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'resp_no',
                        'AttributeType': 'N'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # 等待创建完成
            if not wait_for_table_creation(dynamodb, DynamoDBTables.CHAT_RESPONSES):
                return False
                
        except Exception as e:
            print(f"❌ 创建ChatResponseTable时出错: {str(e)}")
            return False
    
    print(f"\n✅ 表重建完成!")
    print(f"📋 新表结构:")
    print(f"   - {DynamoDBTables.CHAT_RECORDS}: partition_key=user_id, sort_key=id")
    print(f"   - {DynamoDBTables.CHAT_RESPONSES}: partition_key=id, sort_key=resp_no")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("ChatRecordTable 表重建工具")
    print("=" * 60)
    print("⚠️  警告: 此操作将删除现有的ChatRecordTable!")
    print("⚠️  请确保已经导出了数据备份!")
    print("=" * 60)
    
    # 确认操作
    confirm = input("确认要继续吗? (输入 'YES' 确认): ")
    if confirm != 'YES':
        print("❌ 操作已取消")
        sys.exit(0)
    
    success = rebuild_chat_tables()
    
    if success:
        print("\n🎉 表重建完成! 现在可以运行导入脚本恢复数据。")
    else:
        print("\n❌ 表重建失败! 请检查错误信息。")
        sys.exit(1)
