#!/usr/bin/env python3
"""
Word文档处理脚本
用于处理指定路径的Word文档并存储到数据库
"""

import asyncio
import sys
import os
from pathlib import Path
from example_usage import process_word_file_standalone


async def main():
    """主函数"""
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("使用方法: python process_word_doc.py <word_file_path> [doc_category] [chunk_size]")
        print("示例: python process_word_doc.py document.docx '技术文档' 512")
        return
    
    # 获取参数
    file_path = sys.argv[1]
    doc_category = sys.argv[2] if len(sys.argv) > 2 else "Word文档"
    chunk_size = int(sys.argv[3]) if len(sys.argv) > 3 else 512
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在 - {file_path}")
        return
    
    # 检查文件格式
    file_ext = Path(file_path).suffix.lower()
    if file_ext not in ['.docx', '.doc']:
        print(f"错误: 不支持的文件格式 - {file_ext}")
        print("仅支持 .docx 和 .doc 文件")
        return
    
    print(f"开始处理Word文档...")
    print(f"文件路径: {file_path}")
    print(f"文档类别: {doc_category}")
    print(f"分块大小: {chunk_size}")
    print("-" * 50)
    
    try:
        # 处理Word文档
        inserted_ids = await process_word_file_standalone(
            file_path=file_path,
            doc_category=doc_category,
            chunk_size=chunk_size
        )
        
        print("-" * 50)
        print(f"✅ 处理完成!")
        print(f"📄 文件: {Path(file_path).name}")
        print(f"📊 插入记录数: {len(inserted_ids)}")
        print(f"🆔 记录ID: {inserted_ids}")
        
    except Exception as e:
        print("-" * 50)
        print(f"❌ 处理失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)