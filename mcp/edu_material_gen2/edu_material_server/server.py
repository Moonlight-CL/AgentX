#!/usr/bin/env python3
"""
Educational Material Generation MCP Server
提供教育教材生成工具，包括大纲生成和详细内容生成
"""

import logging
import anyio
import click
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import Tool, TextContent


# Import the material generator
from material_generator import EducationalMaterialGenerator

# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('edu_material_gen_mcp_log.log')
    ]
)
logger = logging.getLogger('edu-material-gen-mcp-server')

# Initialize MCP Server
server = Server("edu-material-gen-mcp-server")
server.version = "0.1.0"

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available educational material generation tools"""
    logger.info("List available educational material generation tools...")
    
    try:
        tools = [
        Tool(
            name="generate_educational_outline",
            description="Generate a comprehensive educational material outline for a given subject. This tool creates a structured curriculum outline with multiple chapters, each containing learning objectives, difficulty levels, estimated duration, and detailed descriptions. Perfect for course designers, educators, and content creators who need to plan educational content systematically.",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "The subject or topic for which to generate the educational outline (e.g., 'Python编程', '数据科学基础', '机器学习入门')"
                    },
                    "target_audience": {
                        "type": "string",
                        "description": "The target audience for the educational material (e.g., '初学者', '大学生', '职场人士', '高中生')"
                    },
                    "duration": {
                        "type": "string",
                        "description": "Total duration for the course",
                        "default": "4周"
                    },
                    "difficulty": {
                        "type": "string",
                        "description": "Overall difficulty level of the course",
                        "enum": ["初级", "中级", "高级"],
                        "default": "中级"
                    },
                    "output_format": {
                        "type": "string",
                        "description": "Output format for the outline",
                        "enum": ["json", "markdown"],
                        "default": "json"
                    }
                },
                "required": ["subject", "target_audience"]
            }
        ),
        Tool(
            name="generate_detailed_material",
            description="Generate detailed educational material content prompt for a specific chapter. This tool creates a comprehensive prompt for generating teaching materials including detailed content, practical examples, exercises, key points summary, and references.",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "The subject or topic of the course"
                    },
                    "target_audience": {
                        "type": "string",
                        "description": "The target audience for the educational material"
                    },
                    "chapter_title": {
                        "type": "string",
                        "description": "The title of the chapter for which to generate detailed material"
                    },
                    "chapter_description": {
                        "type": "string",
                        "description": "Description of the chapter content"
                    },
                    "learning_objectives": {
                        "type": "array",
                        "description": "List of learning objectives for this chapter",
                        "items": {
                            "type": "string"
                        }
                    },
                    "estimated_duration": {
                        "type": "string",
                        "description": "Estimated duration for this chapter",
                        "default": "1周"
                    },
                    "difficulty_level": {
                        "type": "string",
                        "description": "Difficulty level of this chapter",
                        "enum": ["初级", "中级", "高级"],
                        "default": "中级"
                    }
                },
                "required": ["subject", "target_audience", "chapter_title", "chapter_description", "learning_objectives"]
            }
        )
        ]
        logger.info(f"Returning {len(tools)} tools")
        return tools
    except Exception as e:
        logger.error(f"Error in list_tools: {str(e)}")
        raise

@server.call_tool()
async def call_tool(name: str, args: dict) -> list[TextContent]:
    """Execute educational material generation tools"""
    
    generator = None
    try:
        logger.info(f"开始执行工具: {name}")
        logger.info(f"工具参数: {args}")
        
        generator = EducationalMaterialGenerator()
        
        if name == "generate_educational_outline":
            subject = args.get("subject")
            target_audience = args.get("target_audience")
            duration = args.get("duration", "4周")
            difficulty = args.get("difficulty", "中级")
            output_format = args.get("output_format", "json")
            
            if not subject:
                raise ValueError("subject parameter is required for outline generation")
            if not target_audience:
                raise ValueError("target_audience parameter is required for outline generation")
            
            logger.info(f"Generating educational outline prompt for subject: {subject}, audience: {target_audience}")
            
            # Generate outline prompt
            prompt = await generator.generate_outline(
                subject=subject,
                target_audience=target_audience,
                duration=duration,
                difficulty=difficulty
            )
            
            # Log the generated prompt
            logger.info(f"生成的大纲提示词 - 主题: {subject}, 受众: {target_audience}")
            logger.info(f"提示词长度: {len(prompt)} 字符")
            logger.info(f"提示词内容预览: {prompt[:500]}...")
            logger.info("=" * 80)
            
            return [TextContent(type="text", text=prompt)]
                
        elif name == "generate_detailed_material":
            subject = args.get("subject")
            target_audience = args.get("target_audience")
            chapter_title = args.get("chapter_title")
            chapter_description = args.get("chapter_description")
            learning_objectives = args.get("learning_objectives", [])
            estimated_duration = args.get("estimated_duration", "1周")
            difficulty_level = args.get("difficulty_level", "中级")
            
            if not subject:
                raise ValueError("subject parameter is required for detailed material generation")
            if not target_audience:
                raise ValueError("target_audience parameter is required for detailed material generation")
            if not chapter_title:
                raise ValueError("chapter_title parameter is required for detailed material generation")
            if not chapter_description:
                raise ValueError("chapter_description parameter is required for detailed material generation")
            if not learning_objectives:
                raise ValueError("learning_objectives parameter is required for detailed material generation")
            
            logger.info(f"Generating detailed material prompt for chapter: {chapter_title}")
            
            # Generate detailed material prompt
            prompt = await generator.generate_detailed_material(
                subject=subject,
                target_audience=target_audience,
                chapter_title=chapter_title,
                chapter_description=chapter_description,
                learning_objectives=learning_objectives,
                estimated_duration=estimated_duration,
                difficulty_level=difficulty_level
            )
            
            # Log the generated prompt
            logger.info(f"生成的详细教材提示词 - 主题: {subject}, 章节: {chapter_title}")
            logger.info(f"目标受众: {target_audience}, 难度: {difficulty_level}")
            logger.info(f"学习目标: {', '.join(learning_objectives)}")
            logger.info(f"提示词长度: {len(prompt)} 字符")
            logger.info(f"提示词内容预览: {prompt[:500]}...")
            logger.info("=" * 80)
            
            return [TextContent(type="text", text=prompt)]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        error_message = f"Error executing tool '{name}': {str(e)}"
        logger.error(error_message)
        logger.error(f"工具执行失败 - 工具名: {name}, 参数: {args}")
        return [TextContent(type="text", text=error_message)]
    
    finally:
        # 确保清理资源
        if generator:
            try:
                await generator.close_connections()
                logger.info(f"工具 {name} 执行完成，资源已清理")
            except Exception as cleanup_error:
                logger.warning(f"清理资源时出错: {cleanup_error}")

@click.command()
@click.option("--transport", type=click.Choice(["stdio", "http"]), default="stdio", help="Transport type")
@click.option("--port", default=3000, help="Port to listen on for HTTP")
def run(transport: str, port: int) -> int:
    """Run the Educational Material Generation MCP Server"""
    
    if transport == 'stdio':
        from mcp.server.stdio import stdio_server

        async def arun():
            async with stdio_server() as (read_stream, write_stream):
                try:
                    logger.info("Starting Educational Material Generation MCP Server")
                    await server.run(
                        read_stream,
                        write_stream,
                        server.create_initialization_options()
                    )
                except Exception as e:
                    logger.error(f"MCP Server Error: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    raise

        anyio.run(arun)
        
    elif transport == 'http':
        session_manager = StreamableHTTPSessionManager(
            app=server,
            json_response=True
        )
        from starlette.applications import Starlette
        from starlette.types import Receive, Scope, Send
        from starlette.routing import Mount, Route
        from starlette.responses import JSONResponse
        import contextlib

        async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
            await session_manager.handle_request(scope, receive, send)

        async def health(request):
            return JSONResponse({'status': 'healthy'})

        @contextlib.asynccontextmanager
        async def lifespan(app: Starlette):
            """Context Manager for Session Manager"""
            try:
                async with session_manager.run():
                    logger.info("Application started with StreamableHTTP session manager!")
                    try:
                        yield
                    finally:
                        logger.info("Application shutting down...")
            except Exception as e:
                logger.error(f"Error in lifespan manager: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                raise

        starlette_app = Starlette(
            routes=[
                Mount("/mcp", app=handle_streamable_http),
                Route("/health", health, methods=["GET"])
            ],
            lifespan=lifespan
        )

        import uvicorn
        uvicorn.run(starlette_app, host="0.0.0.0", port=port)

    return 0

if __name__ == "__main__":
    run()