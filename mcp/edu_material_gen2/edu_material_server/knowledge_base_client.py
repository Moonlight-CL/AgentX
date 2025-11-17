"""
Aurora PostgreSQL数据库客户端
支持基本的CRUD操作和向量数据的存储与查询
"""

import os
import logging
import json
import boto3
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import asyncpg
from dotenv import load_dotenv
import numpy as np
from pgvector.asyncpg import register_vector

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeBaseClient:
    """Aurora PostgreSQL数据库客户端类"""
    
    def __init__(self, region_name: str = None):
        """初始化数据库连接参数"""
        self.host = os.getenv('AURORA_HOST')
        self.port = int(os.getenv('AURORA_PORT', 5432))
        self.database = os.getenv('AURORA_DATABASE')
        self.username = os.getenv('AURORA_USERNAME')
        self.password = os.getenv('AURORA_PASSWORD')
        self.pool = None
        # 从环境变量获取AWS区域，如果没有设置则使用默认值
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')
        self.bedrock_client = None
        
        # 验证必要的环境变量
        if not all([self.host, self.database, self.username, self.password]):
            logger.warning("缺少必要的数据库连接环境变量")
        
        # 初始化Bedrock客户端
        self._init_bedrock_client()
    
    async def init_connection_pool(self, min_size: int = 5, max_size: int = 20):
        """初始化连接池"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                min_size=min_size,
                max_size=max_size,
                init=self._init_connection
            )
            logger.info("数据库连接池初始化成功")
        except Exception as e:
            logger.error(f"数据库连接池初始化失败: {e}")
            raise
    
    async def _init_connection(self, conn):
        """初始化连接时注册向量类型"""
        await register_vector(conn)
    
    async def close_pool(self):
        """关闭连接池"""
        if self.pool:
            await self.pool.close()
            logger.info("数据库连接池已关闭")
    
    def _init_bedrock_client(self):
        """初始化Bedrock客户端"""
        try:
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=self.region_name,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                aws_session_token=os.getenv('AWS_SESSION_TOKEN')  # 可选，用于临时凭证
            )
            logger.info(f"Bedrock客户端初始化成功，区域: {self.region_name}")
        except Exception as e:
            logger.warning(f"Bedrock客户端初始化失败: {e}")
            self.bedrock_client = None
    
    def generate_embedding_with_cohere(self, text: str) -> Optional[List[float]]:
        """
        使用Cohere模型生成文本嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量，如果失败则返回None
        """
        if not self.bedrock_client:
            logger.warning("Bedrock客户端未初始化，无法生成嵌入向量")
            return None
        
        try:
            request_body = {
                "texts": [text],
                "input_type": "search_query"
            }
            
            response = self.bedrock_client.invoke_model(
                modelId="cohere.embed-multilingual-v3",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            
            if 'embeddings' in response_body and len(response_body['embeddings']) > 0:
                embedding = response_body['embeddings'][0]
                
                # 验证向量维度
                if len(embedding) != 1024:
                    logger.warning(f"嵌入向量维度不匹配，期望1024维，实际{len(embedding)}维")
                    return None
                
                return embedding
            
        except Exception as e:
            logger.error(f"生成嵌入向量失败: {e}")
        
        return None
    
    async def search_knowledge_base(self, query: str, limit: int = 5) -> List[str]:
        """
        在知识库中搜索相关文档
        
        Args:
            query: 搜索查询
            limit: 返回结果数量限制
            
        Returns:
            相关文档内容列表
        """
        try:
            # 确保连接池已初始化
            if not self.pool:
                await self.init_connection_pool()
            
            if not self.pool:
                logger.warning("数据库连接池未初始化，无法搜索知识库")
                return []
            
            # 生成查询向量
            query_embedding = self.generate_embedding_with_cohere(query)
            if not query_embedding:
                logger.warning("无法生成查询向量，跳过知识库搜索")
                return []
            
            # 执行向量搜索
            async with self.pool.acquire() as conn:
                # 使用余弦相似度搜索，只查询1024维的向量
                search_query = """
                SELECT content, summary, doc_title, doc_category,
                       1 - (content_vector <=> $1::vector) as similarity
                FROM edu_ref_docs
                WHERE vector_dims(content_vector) = 1024
                  AND 1 - (content_vector <=> $1::vector) > 0.3
                ORDER BY similarity DESC
                LIMIT $2
                """
                
                print(search_query)

                rows = await conn.fetch(search_query, query_embedding, limit)
                
                results = []
                for row in rows:
                    content = f"文档: {row['doc_title']} (类别: {row['doc_category']})\n"
                    content += f"摘要: {row['summary']}\n"
                    content += f"内容: {row['content']}\n"
                    content += f"相似度: {row['similarity']:.3f}"
                    results.append(content)
                
                logger.info(f"知识库搜索完成，找到 {len(results)} 个相关文档")
                return results
                
        except Exception as e:
            logger.error(f"知识库搜索失败: {e}")
            return []
    
    async def search_knowledge_base_detailed(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        在知识库中搜索相关文档，返回详细信息
        
        Args:
            query: 搜索查询
            limit: 返回结果数量限制
            
        Returns:
            包含详细信息的文档列表
        """
        try:
            # 确保连接池已初始化
            if not self.pool:
                await self.init_connection_pool()
            
            if not self.pool:
                logger.warning("数据库连接池未初始化，无法搜索知识库")
                return []
            
            # 生成查询向量
            query_embedding = self.generate_embedding_with_cohere(query)
            if not query_embedding:
                logger.warning("无法生成查询向量，跳过知识库搜索")
                return []
            
            # 执行向量搜索，包含ID字段
            async with self.pool.acquire() as conn:
                # 使用余弦相似度搜索，只查询1024维的向量，包含更多字段
                search_query = """
                SELECT id, content, summary, doc_title, doc_category,
                       1 - (content_vector <=> $1::vector) as similarity
                FROM edu_ref_docs
                WHERE vector_dims(content_vector) = 1024
                  AND 1 - (content_vector <=> $1::vector) > 0.3
                ORDER BY similarity DESC
                LIMIT $2
                """

                rows = await conn.fetch(search_query, query_embedding, limit)
                
                results = []
                for row in rows:
                    result = {
                        'id': row.get('id'),
                        'title': row.get('doc_title'),
                        'type': row.get('doc_category'),
                        'content': row.get('content'),
                        'summary': row.get('summary'),
                        'doc_category': row.get('doc_category'),
                        'similarity': float(row.get('similarity', 0))
                    }
                    results.append(result)
                
                logger.info(f"知识库详细搜索完成，找到 {len(results)} 个相关文档")
                return results
                
        except Exception as e:
            logger.error(f"知识库详细搜索失败: {e}")
            return []
