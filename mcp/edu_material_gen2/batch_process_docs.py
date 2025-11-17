#!/usr/bin/env python3
"""
批量文档处理脚本
用于处理指定目录中的所有文档并存储到数据库
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path
from example_usage import process_directory_documents, get_supported_files


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="批量处理目录中的文档并存储到数据库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 处理当前目录的所有文档
  python batch_process_docs.py ./documents

  # 处理指定目录，设置文档类别
  python batch_process_docs.py ./documents --category "技术文档"

  # 非递归处理，只处理当前目录
  python batch_process_docs.py ./documents --no-recursive

  # 设置分块大小和并发数
  python batch_process_docs.py ./documents --chunk-size 256 --max-concurrent 5

  # 预览模式，只显示文件列表不实际处理
  python batch_process_docs.py ./documents --preview
        """
    )
    
    parser.add_argument(
        'directory',
        help='要处理的文档目录路径'
    )
    
    parser.add_argument(
        '--category', '-c',
        default='批量文档',
        help='文档类别 (默认: 批量文档)'
    )
    
    parser.add_argument(
        '--chunk-size', '-s',
        type=int,
        default=512,
        help='分块大小 (默认: 512)'
    )
    
    parser.add_argument(
        '--max-concurrent', '-m',
        type=int,
        default=3,
        help='最大并发处理数量 (默认: 3)'
    )
    
    parser.add_argument(
        '--no-recursive', '-nr',
        action='store_true',
        help='不递归处理子目录'
    )
    
    parser.add_argument(
        '--preview', '-p',
        action='store_true',
        help='预览模式，只显示文件列表不实际处理'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细输出'
    )
    
    return parser.parse_args()


def preview_files(directory_path: str, recursive: bool = True):
    """预览模式，显示将要处理的文件"""
    print(f"📁 预览目录: {directory_path}")
    print(f"🔄 递归处理: {'是' if recursive else '否'}")
    print("-" * 50)
    
    try:
        files = get_supported_files(directory_path, recursive)
        
        if not files:
            print("❌ 没有找到支持的文档文件")
            print("支持的格式: .txt, .docx, .doc")
            return
        
        print(f"📄 发现 {len(files)} 个支持的文档文件:\n")
        
        # 按文件类型分组显示
        file_types = {}
        for file_path in files:
            ext = file_path.suffix.lower()
            if ext not in file_types:
                file_types[ext] = []
            file_types[ext].append(file_path)
        
        for ext, file_list in sorted(file_types.items()):
            print(f"  {ext.upper()} 文件 ({len(file_list)} 个):")
            for file_path in sorted(file_list):
                # 显示相对路径
                try:
                    rel_path = file_path.relative_to(Path(directory_path))
                    print(f"    📄 {rel_path}")
                except ValueError:
                    print(f"    📄 {file_path}")
            print()
        
        # 显示统计信息
        total_size = sum(f.stat().st_size for f in files if f.exists())
        print(f"📊 统计信息:")
        print(f"  - 总文件数: {len(files)}")
        print(f"  - 总大小: {total_size / 1024 / 1024:.2f} MB")
        print(f"  - 文件类型: {', '.join(sorted(file_types.keys()))}")
        
    except Exception as e:
        print(f"❌ 预览失败: {e}")


async def main():
    """主函数"""
    args = parse_arguments()
    
    # 验证目录路径
    if not os.path.exists(args.directory):
        print(f"❌ 错误: 目录不存在 - {args.directory}")
        return 1
    
    if not os.path.isdir(args.directory):
        print(f"❌ 错误: 路径不是目录 - {args.directory}")
        return 1
    
    # 预览模式
    if args.preview:
        preview_files(args.directory, not args.no_recursive)
        return 0
    
    # 显示处理参数
    print("🚀 批量文档处理器")
    print("=" * 50)
    print(f"📁 目录路径: {args.directory}")
    print(f"📂 文档类别: {args.category}")
    print(f"📏 分块大小: {args.chunk_size}")
    print(f"🔄 递归处理: {'是' if not args.no_recursive else '否'}")
    print(f"⚡ 最大并发: {args.max_concurrent}")
    print(f"📝 详细输出: {'是' if args.verbose else '否'}")
    print("=" * 50)
    
    # 确认处理
    try:
        confirm = input("\n是否继续处理? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes', '是']:
            print("❌ 用户取消处理")
            return 0
    except KeyboardInterrupt:
        print("\n❌ 用户中断处理")
        return 0
    
    print("\n🔄 开始批量处理...\n")
    
    try:
        # 执行批量处理
        result = await process_directory_documents(
            directory_path=args.directory,
            doc_category=args.category,
            chunk_size=args.chunk_size,
            recursive=not args.no_recursive,
            max_concurrent=args.max_concurrent
        )
        
        # 显示最终结果
        print("\n" + "🎉 批量处理完成!" + "\n")
        
        if args.verbose and result['results']:
            print("📋 详细结果:")
            for file_result in result['results']:
                status = "✅" if file_result['success'] else "❌"
                print(f"  {status} {file_result['file_name']}: {file_result['records_count']} 条记录 "
                      f"({file_result['processing_time']}秒)")
        
        return 0 if result['failed_files'] == 0 else 1
        
    except KeyboardInterrupt:
        print("\n❌ 处理被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 处理失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ 程序被中断")
        sys.exit(1)