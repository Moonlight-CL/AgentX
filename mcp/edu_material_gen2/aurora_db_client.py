"""
Aurora PostgreSQL数据库客户端
支持基本的CRUD操作和向量数据的存储与查询
"""

import os
import logging
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


class AuroraDBClient:
    """Aurora PostgreSQL数据库客户端类"""
    
    def __init__(self):
        """初始化数据库连接参数"""
        self.host = os.getenv('AURORA_HOST')
        self.port = int(os.getenv('AURORA_PORT', 5432))
        self.database = os.getenv('AURORA_DATABASE')
        self.username = os.getenv('AURORA_USERNAME')
        self.password = os.getenv('AURORA_PASSWORD')
        self.pool = None
        
        # 验证必要的环境变量
        if not all([self.host, self.database, self.username, self.password]):
            raise ValueError("缺少必要的数据库连接环境变量")
    
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
    
    async def create_table(self, table_name: str, schema: Dict[str, str]):
        """
        创建表
        
        Args:
            table_name: 表名
            schema: 表结构字典，格式为 {'column_name': 'column_type'}
        """
        columns = []
        for col_name, col_type in schema.items():
            columns.append(f"{col_name} {col_type}")
        
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {', '.join(columns)}
        )
        """
        
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(create_sql)
                logger.info(f"表 {table_name} 创建成功")
            except Exception as e:
                logger.error(f"创建表 {table_name} 失败: {e}")
                raise
    
    async def insert_record(self, table_name: str, data: Dict[str, Any]) -> int:
        """
        插入记录
        
        Args:
            table_name: 表名
            data: 要插入的数据字典
            
        Returns:
            插入记录的ID（如果有自增ID列）
        """
        columns = list(data.keys())
        placeholders = [f"${i+1}" for i in range(len(columns))]
        values = list(data.values())
        
        insert_sql = f"""
        INSERT INTO {table_name} ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        RETURNING id
        """
        
        async with self.pool.acquire() as conn:
            try:
                result = await conn.fetchval(insert_sql, *values)
                logger.info(f"成功插入记录到表 {table_name}")
                return result
            except Exception as e:
                logger.error(f"插入记录到表 {table_name} 失败: {e}")
                raise
    
    async def select_records(self, 
                           table_name: str, 
                           where_clause: str = None, 
                           params: List[Any] = None,
                           limit: int = None) -> List[Dict[str, Any]]:
        """
        查询记录
        
        Args:
            table_name: 表名
            where_clause: WHERE条件子句
            params: 查询参数
            limit: 限制返回记录数
            
        Returns:
            查询结果列表
        """
        select_sql = f"SELECT * FROM {table_name}"
        
        if where_clause:
            select_sql += f" WHERE {where_clause}"
        
        if limit:
            select_sql += f" LIMIT {limit}"
        
        async with self.pool.acquire() as conn:
            try:
                if params:
                    rows = await conn.fetch(select_sql, *params)
                else:
                    rows = await conn.fetch(select_sql)
                
                # 转换为字典列表
                results = [dict(row) for row in rows]
                logger.info(f"从表 {table_name} 查询到 {len(results)} 条记录")
                return results
            except Exception as e:
                logger.error(f"查询表 {table_name} 失败: {e}")
                raise
    
    async def update_record(self, 
                          table_name: str, 
                          data: Dict[str, Any], 
                          where_clause: str, 
                          where_params: List[Any]) -> int:
        """
        更新记录
        
        Args:
            table_name: 表名
            data: 要更新的数据字典
            where_clause: WHERE条件子句（使用占位符如 'id = $1'）
            where_params: WHERE条件参数
            
        Returns:
            受影响的记录数
        """
        set_clauses = []
        values = []
        param_index = 1
        
        # 构建SET子句
        for col_name, col_value in data.items():
            set_clauses.append(f"{col_name} = ${param_index}")
            values.append(col_value)
            param_index += 1
        
        # 重新构建WHERE子句，调整参数索引
        where_clause_adjusted = where_clause
        for i, param in enumerate(where_params):
            # 替换WHERE子句中的参数占位符
            old_placeholder = f"${i+1}"
            new_placeholder = f"${param_index}"
            where_clause_adjusted = where_clause_adjusted.replace(old_placeholder, new_placeholder)
            values.append(param)
            param_index += 1
        
        update_sql = f"""
        UPDATE {table_name} 
        SET {', '.join(set_clauses)}
        WHERE {where_clause_adjusted}
        """
        
        async with self.pool.acquire() as conn:
            try:
                result = await conn.execute(update_sql, *values)
                affected_rows = int(result.split()[-1])
                logger.info(f"更新表 {table_name} 中 {affected_rows} 条记录")
                return affected_rows
            except Exception as e:
                logger.error(f"更新表 {table_name} 失败: {e}")
                raise
    
    async def delete_record(self, 
                          table_name: str, 
                          where_clause: str, 
                          where_params: List[Any]) -> int:
        """
        删除记录
        
        Args:
            table_name: 表名
            where_clause: WHERE条件子句
            where_params: WHERE条件参数
            
        Returns:
            删除的记录数
        """
        delete_sql = f"DELETE FROM {table_name} WHERE {where_clause}"
        
        async with self.pool.acquire() as conn:
            try:
                result = await conn.execute(delete_sql, *where_params)
                deleted_rows = int(result.split()[-1])
                logger.info(f"从表 {table_name} 删除 {deleted_rows} 条记录")
                return deleted_rows
            except Exception as e:
                logger.error(f"删除表 {table_name} 记录失败: {e}")
                raise
    
    async def insert_vector_record(self, 
                                 table_name: str, 
                                 data: Dict[str, Any], 
                                 vector_column: str, 
                                 vector_data: List[float]) -> int:
        """
        插入包含向量数据的记录
        
        Args:
            table_name: 表名
            data: 基础数据字典
            vector_column: 向量列名
            vector_data: 向量数据
            
        Returns:
            插入记录的ID
        """
        # 将向量数据添加到数据字典中
        data[vector_column] = vector_data
        
        columns = list(data.keys())
        placeholders = [f"${i+1}" for i in range(len(columns))]
        values = list(data.values())
        
        insert_sql = f"""
        INSERT INTO {table_name} ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        RETURNING id
        """
        
        async with self.pool.acquire() as conn:
            try:
                result = await conn.fetchval(insert_sql, *values)
                logger.info(f"成功插入向量记录到表 {table_name}")
                return result
            except Exception as e:
                logger.error(f"插入向量记录到表 {table_name} 失败: {e}")
                raise
    
    async def vector_similarity_search(self, 
                                     table_name: str, 
                                     vector_column: str, 
                                     query_vector: List[float], 
                                     limit: int = 10,
                                     similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        向量相似度搜索
        
        Args:
            table_name: 表名
            vector_column: 向量列名
            query_vector: 查询向量
            limit: 返回结果数量限制
            similarity_threshold: 相似度阈值
            
        Returns:
            相似度搜索结果列表，包含相似度分数
        """
        search_sql = f"""
        SELECT *, 
               1 - ({vector_column} <=> $1) as similarity_score
        FROM {table_name}
        WHERE 1 - ({vector_column} <=> $1) > $2
        ORDER BY {vector_column} <=> $1
        LIMIT $3
        """
        
        async with self.pool.acquire() as conn:
            try:
                rows = await conn.fetch(search_sql, query_vector, similarity_threshold, limit)
                results = [dict(row) for row in rows]
                logger.info(f"向量搜索返回 {len(results)} 条结果")
                return results
            except Exception as e:
                logger.error(f"向量相似度搜索失败: {e}")
                raise
    
    async def create_vector_index(self, table_name: str, vector_column: str, index_type: str = "ivfflat"):
        """
        为向量列创建索引
        
        Args:
            table_name: 表名
            vector_column: 向量列名
            index_type: 索引类型 (ivfflat 或 hnsw)
        """
        index_name = f"idx_{table_name}_{vector_column}_{index_type}"
        
        if index_type == "ivfflat":
            create_index_sql = f"""
            CREATE INDEX IF NOT EXISTS {index_name} 
            ON {table_name} 
            USING ivfflat ({vector_column} vector_cosine_ops)
            WITH (lists = 100)
            """
        elif index_type == "hnsw":
            create_index_sql = f"""
            CREATE INDEX IF NOT EXISTS {index_name} 
            ON {table_name} 
            USING hnsw ({vector_column} vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
            """
        else:
            raise ValueError(f"不支持的索引类型: {index_type}")
        
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(create_index_sql)
                logger.info(f"成功为表 {table_name} 的列 {vector_column} 创建 {index_type} 索引")
            except Exception as e:
                logger.error(f"创建向量索引失败: {e}")
                raise


# 使用示例
async def example_usage():
    """使用示例"""
    db_client = AuroraDBClient()
    
    try:
        # 初始化连接池
        await db_client.init_connection_pool()
        
        # 创建示例表（包含向量列）
        schema = {
            'id': 'SERIAL PRIMARY KEY',
            'title': 'VARCHAR(255)',
            'content': 'TEXT',
            'embedding': 'vector(1536)',  # 1536维向量，适用于OpenAI embeddings
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
        await db_client.create_table('documents', schema)
        
        # 插入向量记录
        sample_vector = [0.1] * 1536  # 示例向量
        record_id = await db_client.insert_vector_record(
            'documents',
            {'title': '示例文档', 'content': '这是一个示例文档'},
            'embedding',
            sample_vector
        )
        
        # 查询记录
        records = await db_client.select_records('documents', 'id = $1', [record_id])
        print(f"查询结果: {records}")
        
        # 向量相似度搜索
        query_vector = [0.1] * 1536
        similar_docs = await db_client.vector_similarity_search(
            'documents', 
            'embedding', 
            query_vector, 
            limit=5
        )
        print(f"相似文档: {similar_docs}")
        
        # 创建向量索引
        await db_client.create_vector_index('documents', 'embedding', 'ivfflat')
        
    finally:
        # 关闭连接池
        await db_client.close_pool()


if __name__ == "__main__":
    asyncio.run(example_usage())