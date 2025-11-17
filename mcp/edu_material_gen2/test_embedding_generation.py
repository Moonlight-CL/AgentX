#!/usr/bin/env python3
"""
测试嵌入向量生成功能
"""

import asyncio
import logging
from edu_material_server.knowledge_base_client import KnowledgeBaseClient

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_embedding_generation():
    """测试嵌入向量生成"""
    
    try:
        # 初始化客户端
        client = KnowledgeBaseClient()
        
        # 测试文本
        test_texts = [
            "大学计算机基础",
            "Python编程入门",
            "数据结构与算法",
            "机器学习基础概念"
        ]
        
        logger.info("开始测试嵌入向量生成...")
        
        for i, text in enumerate(test_texts, 1):
            logger.info(f"测试文本 {i}: {text}")
            
            # 生成嵌入向量
            embedding = client.generate_embedding_with_cohere(text)
            
            if embedding:
                logger.info(f"  ✓ 成功生成嵌入向量，维度: {len(embedding)}")
                logger.info(f"  ✓ 向量前5个值: {embedding[:5]}")
            else:
                logger.error(f"  ✗ 嵌入向量生成失败")
        
        # 测试知识库搜索
        logger.info("\n开始测试知识库搜索...")
        
        await client.init_connection_pool()
        
        search_query = "大学计算机基础"
        results = await client.search_knowledge_base(search_query, limit=3)
        
        logger.info(f"搜索查询: {search_query}")
        logger.info(f"找到 {len(results)} 个相关文档")
        
        for i, result in enumerate(results, 1):
            logger.info(f"结果 {i}:")
            # 只显示前200个字符
            preview = result[:200] + "..." if len(result) > 200 else result
            logger.info(f"  {preview}")
        
        await client.close_pool()
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_embedding_generation())