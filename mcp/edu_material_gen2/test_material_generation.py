#!/usr/bin/env python3
"""
测试教材生成功能
"""

import asyncio
import logging
from edu_material_server.material_generator import EducationalMaterialGenerator

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_material_generation():
    """测试教材生成功能"""
    
    try:
        # 初始化生成器
        generator = EducationalMaterialGenerator()
        
        logger.info("开始测试教材大纲生成...")
        
        # 测试大纲生成
        subject = "大学计算机基础"
        target_audience = "大一新生"
        
        logger.info(f"学科主题: {subject}")
        logger.info(f"目标受众: {target_audience}")
        
        # 生成大纲prompt
        outline_prompt = await generator.generate_outline(
            subject=subject,
            target_audience=target_audience,
            duration="8周",
            difficulty="初级"
        )
        
        logger.info("✓ 大纲生成成功")
        logger.info(f"生成的prompt长度: {len(outline_prompt)} 字符")
        
        # 显示prompt的前500个字符
        preview = outline_prompt[:500] + "..." if len(outline_prompt) > 500 else outline_prompt
        logger.info(f"Prompt预览:\n{preview}")
        
        # 测试详细教材生成
        logger.info("\n开始测试详细教材生成...")
        
        detailed_prompt = await generator.generate_detailed_material(
            subject=subject,
            target_audience=target_audience,
            chapter_title="计算机系统概述",
            chapter_description="介绍计算机系统的基本组成和工作原理",
            learning_objectives=["了解计算机硬件组成", "理解计算机工作原理", "掌握基本概念"],
            estimated_duration="1周",
            difficulty_level="初级"
        )
        
        logger.info("✓ 详细教材生成成功")
        logger.info(f"生成的prompt长度: {len(detailed_prompt)} 字符")
        
        # 显示prompt的前500个字符
        preview = detailed_prompt[:500] + "..." if len(detailed_prompt) > 500 else detailed_prompt
        logger.info(f"Prompt预览:\n{preview}")
        
        # 关闭连接
        await generator.close_connections()
        
        logger.info("\n✓ 所有测试完成，没有发现维度错误")
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_material_generation())