#!/usr/bin/env python3
"""
ChatRecordTable数据导入脚本
将导出的JSON数据导入到新的ChatRecordTable结构中
"""

import json
import boto3
from datetime import datetime
import os
import sys
import glob

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.utils.aws_config import get_aws_region, DynamoDBTables

def find_backup_file():
    """查找最新的备份文件"""
    backup_files = glob.glob('chat_records_backup_*.json')
    if not backup_files:
        return None
    
    # 按文件名排序，获取最新的
    backup_files.sort(reverse=True)
    return backup_files[0]

def import_chat_records(backup_file=None):
    """导入ChatRecord数据到新表结构"""
    
    # 查找备份文件
    if not backup_file:
        backup_file = find_backup_file()
        if not backup_file:
            print("❌ 未找到备份文件! 请先运行导出脚本。")
            return False
    
    if not os.path.exists(backup_file):
        print(f"❌ 备份文件不存在: {backup_file}")
        return False
    
    print(f"📁 使用备份文件: {backup_file}")
    
    # 读取备份数据
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        chat_records = backup_data.get('chat_records', [])
        
        print(f"📊 备份数据统计:")
        print(f"   - ChatRecord记录数: {len(chat_records)}")
        
    except Exception as e:
        print(f"❌ 读取备份文件时出错: {str(e)}")
        return False
    
    # 初始化DynamoDB资源
    aws_region = get_aws_region()
    dynamodb = boto3.resource('dynamodb', region_name=aws_region)
    
    print(f"\n开始导入数据到新表结构...")
    print(f"AWS Region: {aws_region}")
    
    # 获取新表
    try:
        chat_record_table = dynamodb.Table(DynamoDBTables.CHAT_RECORDS)
        
        # 检查表是否存在且为新结构
        chat_record_table.load()
        if chat_record_table.key_schema[0]['AttributeName'] != 'user_id':
            print("❌ ChatRecordTable不是新结构! 请先运行表重建脚本。")
            return False
            
    except Exception as e:
        print(f"❌ 获取表时出错: {str(e)}")
        print("请确保已经运行了表重建脚本。")
        return False
    
    # 导入ChatRecord数据
    print(f"\n📥 导入ChatRecord数据...")
    imported_records = 0
    failed_records = 0
    
    for record in chat_records:
        try:
            # 确保user_id存在
            if not record.get('user_id'):
                record['user_id'] = 'public'
            
            # 使用新的key结构导入
            chat_record_table.put_item(Item=record)
            imported_records += 1
            
            if imported_records % 10 == 0:
                print(f"   已导入 {imported_records} 条记录...")
                
        except Exception as e:
            print(f"   ❌ 导入记录失败 (id: {record.get('id', 'unknown')}): {str(e)}")
            failed_records += 1
    
    print(f"✅ ChatRecord导入完成: {imported_records} 成功, {failed_records} 失败")
    
    # 验证导入结果
    print(f"\n🔍 验证导入结果...")
    try:
        # 检查几个用户的记录
        test_users = set()
        for record in chat_records[:10]:  # 检查前10条记录的用户
            test_users.add(record.get('user_id', 'public'))
        
        for user_id in test_users:
            response = chat_record_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id),
                Limit=5
            )
            user_records = len(response.get('Items', []))
            print(f"   用户 {user_id}: {user_records} 条记录")
            
    except Exception as e:
        print(f"   ⚠️  验证时出错: {str(e)}")
    
    # 总结
    print(f"\n📊 导入总结:")
    print(f"   - ChatRecord: {imported_records}/{len(chat_records)} 成功")
    
    if failed_records == 0:
        print(f"🎉 所有数据导入成功!")
        return True
    else:
        print(f"⚠️  部分数据导入失败，请检查错误信息。")
        return imported_records > 0

if __name__ == "__main__":
    print("=" * 60)
    print("ChatRecordTable 数据导入工具")
    print("=" * 60)
    
    # 检查命令行参数
    backup_file = None
    if len(sys.argv) > 1:
        backup_file = sys.argv[1]
        print(f"使用指定的备份文件: {backup_file}")
    else:
        print("自动查找最新的备份文件...")
    
    success = import_chat_records(backup_file)
    
    if success:
        print("\n🎉 数据导入完成!")
        print("💡 提示: 现在可以更新应用代码以使用新的表结构。")
    else:
        print("\n❌ 数据导入失败! 请检查错误信息。")
        sys.exit(1)
