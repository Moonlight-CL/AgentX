#!/usr/bin/env python3
"""
Educational Material Generator
提供教育教材生成功能，包括大纲生成和详细内容生成
"""

import logging
import os
from typing import List
from dataclasses import dataclass
from dotenv import load_dotenv
from knowledge_base_client import KnowledgeBaseClient

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class OutlineItem:
    """教材大纲项目"""
    title: str
    description: str
    estimated_duration: str  # 预计学习时长
    difficulty_level: str    # 难度等级
    learning_objectives: List[str]  # 学习目标

@dataclass
class MaterialOutline:
    """教材大纲"""
    subject: str
    target_audience: str
    total_duration: str
    outline_items: List[OutlineItem]

@dataclass
class DetailedMaterial:
    """详细教材内容"""
    title: str
    content: str
    examples: List[str]
    exercises: List[str]
    key_points: List[str]
    references: List[str]

class EducationalMaterialGenerator:
    """教育教材生成器"""
    
    def __init__(self, region_name: str = None):
        """初始化生成器"""
        # 从环境变量获取AWS区域，如果没有设置则使用默认值
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')
        self.db_client = None
    
    async def _init_db_client(self):
        """初始化数据库客户端"""
        if not self.db_client:
            try:
                self.db_client = KnowledgeBaseClient(region_name=self.region_name)
                await self.db_client.init_connection_pool()
                logger.info("数据库客户端初始化成功")
            except Exception as e:
                logger.warning(f"数据库客户端初始化失败: {e}")
                self.db_client = None
    
    async def _search_knowledge_base(self, query: str, limit: int = 5) -> List[str]:
        """
        在知识库中搜索相关文档
        
        Args:
            query: 搜索查询
            limit: 返回结果数量限制
            
        Returns:
            相关文档内容列表
        """
        try:
            # 初始化数据库客户端
            await self._init_db_client()
            
            if not self.db_client:
                logger.warning("数据库客户端未初始化，无法搜索知识库")
                return []
            
            # 使用数据库客户端搜索知识库，获取详细结果
            results = await self.db_client.search_knowledge_base_detailed(query, limit)
            
            # 记录搜索结果的详细信息
            logger.info(f"知识库搜索结果详情 - 查询: '{query}', 找到 {len(results)} 个文档:")
            for i, result in enumerate(results, 1):
                logger.info(f"文档 {i}:")
                logger.info(f"  ID: {result.get('id', 'N/A')}")
                logger.info(f"  类型: {result.get('type', result.get('doc_category', 'N/A'))}")
                logger.info(f"  标题: {result.get('title', result.get('doc_title', 'N/A'))}")
                logger.info(f"  内容长度: {len(result.get('content', ''))} 字符")
                logger.info(f"  相似度: {result.get('similarity', 'N/A')}")
                logger.info(f"  内容预览: {result.get('content', '')[:200]}...")
            
            # 转换为原有格式返回
            formatted_results = []
            for result in results:
                content = f"文档: {result.get('title', result.get('doc_title', 'Unknown'))} (类别: {result.get('type', result.get('doc_category', 'Unknown'))})\n"
                content += f"摘要: {result.get('summary', 'N/A')}\n"
                content += f"内容: {result.get('content', '')}\n"
                content += f"相似度: {result.get('similarity', 0):.3f}"
                formatted_results.append(content)
            
            return formatted_results
                
        except Exception as e:
            logger.error(f"知识库搜索失败: {e}")
            return []
    
    async def close_connections(self):
        """关闭所有连接"""
        if self.db_client:
            await self.db_client.close_pool()
    
    async def generate_outline(self, subject: str, target_audience: str, 
                        duration: str = "4周", difficulty: str = "中级") -> str:
        """
        生成教育教材大纲的prompt
        
        Args:
            subject: 学科主题
            target_audience: 目标受众
            duration: 总时长
            difficulty: 难度等级
            
        Returns:
            str: 生成大纲的prompt文本
        """
        logger.info(f"Generating outline prompt for subject: {subject}, audience: {target_audience}")
        
        # 构建搜索查询
        search_query = f"{subject} 教材大纲 课程设计 {target_audience} {difficulty}"
        
        # 搜索知识库获取相关参考资料
        reference_docs = await self._search_knowledge_base(search_query, limit=3)
        
        # 构建基础prompt
        prompt = f"""请为以下教育课程生成详细的教材大纲：

学科主题: {subject}
目标受众: {target_audience}
总时长: {duration}
难度等级: {difficulty}"""

        # 如果找到相关参考资料，添加到prompt中
        if reference_docs:
            prompt += f"""

参考资料:
以下是从知识库中找到的相关参考资料，请参考这些内容来设计更专业和全面的教材大纲：

"""
            for i, doc in enumerate(reference_docs, 1):
                prompt += f"参考资料 {i}:\n{doc}\n\n"
            
            prompt += """请基于上述参考资料和你的专业知识，"""
        else:
            prompt += """

请基于你的专业知识，"""

        prompt += """生成一个包含8-12个章节的详细大纲，每个章节包括：
1. 章节标题
2. 章节描述
3. 预计学习时长
4. 难度等级
5. 学习目标（3-5个）

请以JSON格式返回，结构如下：
{
    "subject": "学科主题",
    "target_audience": "目标受众",
    "total_duration": "总时长",
    "outline_items": [
        {
            "title": "章节标题",
            "description": "章节描述",
            "estimated_duration": "预计时长",
            "difficulty_level": "难度等级",
            "learning_objectives": ["目标1", "目标2", "目标3"]
        }
    ]
}"""
        
        return prompt
    
    async def generate_detailed_material(self, subject: str, target_audience: str, 
                                 chapter_title: str, chapter_description: str,
                                 learning_objectives: List[str], estimated_duration: str,
                                 difficulty_level: str) -> str:
        """
        根据章节信息生成详细教材内容的prompt
        
        Args:
            subject: 课程主题
            target_audience: 目标受众
            chapter_title: 章节标题
            chapter_description: 章节描述
            learning_objectives: 学习目标
            estimated_duration: 预计时长
            difficulty_level: 难度等级
            
        Returns:
            str: 生成详细教材的prompt文本
        """
        logger.info(f"Generating detailed material prompt for chapter: {chapter_title}")
        
        # 构建搜索查询
        search_query = f"{subject} {chapter_title} {chapter_description} 教学内容 案例 练习"
        
        # 搜索知识库获取相关参考资料
        reference_docs = await self._search_knowledge_base(search_query, limit=3)
        
        # 构建基础prompt
        prompt = f"""请为以下教育课程章节生成详细的教材内容：

课程主题: {subject}
目标受众: {target_audience}
章节标题: {chapter_title}
章节描述: {chapter_description}
学习目标: {', '.join(learning_objectives)}
预计时长: {estimated_duration}
难度等级: {difficulty_level}"""

        # 如果找到相关参考资料，添加到prompt中
        if reference_docs:
            prompt += f"""

参考资料:
以下是从知识库中找到的相关参考资料，请参考这些内容来创建更丰富和准确的教学材料：

"""
            for i, doc in enumerate(reference_docs, 1):
                prompt += f"参考资料 {i}:\n{doc}\n\n"
            
            prompt += """请基于上述参考资料和你的专业知识，"""
        else:
            prompt += """

请基于你的专业知识，"""

        prompt += """生成包含以下内容的详细教材：
1. 详细的教学内容（至少1000字）
2. 实际案例和例子（3-5个）
3. 练习题和作业（5-8个）
4. 关键知识点总结（5-10个）
5. 参考资料和延伸阅读（3-5个）

请以JSON格式返回，结构如下：
{
    "title": "章节标题",
    "content": "详细教学内容",
    "examples": ["例子1", "例子2", "例子3"],
    "exercises": ["练习1", "练习2", "练习3"],
    "key_points": ["要点1", "要点2", "要点3"],
    "references": ["参考1", "参考2", "参考3"]
}"""
        
        return prompt
    
