#!/usr/bin/env python3
"""
ChatRecordTable完整迁移脚本
一键完成数据导出、表重建和数据导入的完整流程
"""

import os
import sys
import subprocess
import time
from datetime import datetime

def run_script(script_name, description):
    """运行指定的脚本"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    
    try:
        # 运行脚本
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, 
                              text=True, 
                              cwd=os.path.dirname(__file__))
        
        # 输出脚本的标准输出
        if result.stdout:
            print(result.stdout)
        
        # 如果有错误输出，也显示
        if result.stderr:
            print("错误输出:")
            print(result.stderr)
        
        # 检查返回码
        if result.returncode == 0:
            print(f"✅ {description} 完成")
            return True
        else:
            print(f"❌ {description} 失败 (返回码: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ 运行脚本时出错: {str(e)}")
        return False

def migrate_chat_tables():
    """执行完整的ChatRecordTable迁移流程"""
    
    print("🔄 ChatRecordTable 完整迁移流程")
    print("=" * 60)
    print("此脚本将执行以下步骤:")
    print("1. 导出现有数据到JSON文件")
    print("2. 删除旧表并创建新表结构")
    print("3. 将数据导入到新表中")
    print("=" * 60)
    
    # 确认操作
    print("⚠️  警告: 此操作将重建ChatRecordTable!")
    print("⚠️  请确保没有其他程序正在使用该表!")
    confirm = input("\n确认要继续吗? (输入 'YES' 确认): ")
    if confirm != 'YES':
        print("❌ 操作已取消")
        return False
    
    start_time = time.time()
    
    # 步骤1: 导出数据
    if not run_script('export_chat_records.py', '步骤1: 导出现有数据'):
        print("\n❌ 数据导出失败，迁移终止")
        return False
    
    # 等待一下，确保文件写入完成
    time.sleep(2)
    
    # 步骤2: 重建表结构
    print(f"\n⏳ 准备重建表结构...")
    print("注意: 表重建过程中会有确认提示，请输入 'YES' 确认")
    
    # 为重建脚本准备自动确认
    rebuild_script = os.path.join(os.path.dirname(__file__), 'rebuild_chat_tables.py')
    try:
        # 使用echo来自动提供YES确认
        result = subprocess.run(f'echo "YES" | {sys.executable} {rebuild_script}', 
                              shell=True, 
                              capture_output=True, 
                              text=True,
                              cwd=os.path.dirname(__file__))
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("错误输出:")
            print(result.stderr)
        
        if result.returncode != 0:
            print(f"❌ 步骤2: 重建表结构 失败 (返回码: {result.returncode})")
            return False
        else:
            print("✅ 步骤2: 重建表结构 完成")
            
    except Exception as e:
        print(f"❌ 重建表结构时出错: {str(e)}")
        return False
    
    # 等待表创建完全完成
    print("⏳ 等待表创建完全完成...")
    time.sleep(10)
    
    # 步骤3: 导入数据
    if not run_script('import_chat_records.py', '步骤3: 导入数据到新表'):
        print("\n❌ 数据导入失败")
        print("💡 提示: 数据已导出到JSON文件，可以稍后手动导入")
        return False
    
    # 计算总耗时
    total_time = time.time() - start_time
    minutes = int(total_time // 60)
    seconds = int(total_time % 60)
    
    print(f"\n🎉 ChatRecordTable迁移完成!")
    print(f"⏱️  总耗时: {minutes}分{seconds}秒")
    print(f"📋 迁移总结:")
    print(f"   ✅ 数据已导出到JSON备份文件")
    print(f"   ✅ 表结构已更新 (partition_key: user_id, sort_key: id)")
    print(f"   ✅ 数据已导入到新表结构")
    print(f"\n💡 下一步:")
    print(f"   - 更新应用代码以使用新的表结构")
    print(f"   - 测试应用功能是否正常")
    print(f"   - 确认无误后可删除备份文件")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("ChatRecordTable 完整迁移工具")
    print("=" * 60)
    
    success = migrate_chat_tables()
    
    if success:
        print("\n🎉 迁移成功完成!")
    else:
        print("\n❌ 迁移失败!")
        print("💡 提示: 可以单独运行各个脚本进行故障排除:")
        print("   - python export_chat_records.py")
        print("   - python rebuild_chat_tables.py") 
        print("   - python import_chat_records.py")
        sys.exit(1)
