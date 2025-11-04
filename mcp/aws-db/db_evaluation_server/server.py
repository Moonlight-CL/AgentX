#!/usr/bin/env python3
"""
AWS RDS Pricing Analysis MCP Server
提供RDS MySQL定价分析工具，包括Aurora多代转换分析和扩展支持定价分析
"""

import logging
import anyio
import click
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import Tool, TextContent
from pydantic import AnyUrl

# Import the pricing analyzers and sysbench analyzer
from .rds_aurora_multi_generation_pricing_analyzer import RDSAuroraMultiGenerationPricingAnalyzer
from .rds_mysql_extend_support_pricing_analyzer import RDSPricingAnalyzer
from .mysql_sysbench_analyzer import MySQLSysbenchAnalyzer, MySQLClusterConfig, SysbenchTestConfig

# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('aws_rds_pricing_analysis_mcp_log.log')
    ]
)
logger = logging.getLogger('aws-rds-pricing-analysis-mcp-server')

# Initialize MCP Server
server = Server("aws-rds-pricing-analysis-mcp-server")
server.version = "0.1.0"

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available AWS RDS pricing analysis tools"""
    logger.info("List available pricing analysis tools...")

    return [
        Tool(
            name="analyze_aurora_multi_generation_pricing",
            description="Analyze RDS MySQL instances and calculate Aurora conversion costs with multi-generation support (r7g, r8g). This tool provides comprehensive pricing analysis including instance costs, storage costs, and total MRR for Aurora migration scenarios. It supports various architectures including Single-AZ, Multi-AZ, TAZ clusters, and RDS MySQL clusters. The analysis includes both Aurora Standard and IO Optimized configurations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "AWS region for analysis (e.g., us-east-1, ap-northeast-1)"
                    },
                    "output_format": {
                        "type": "string",
                        "description": "Output format for results",
                        "enum": ["json", "csv", "markdown"],
                        "default": "json"
                    },
                },
                "required": ["region"]
            }
        ),
        Tool(
            name="analyze_mysql_extended_support_pricing",
            description="Analyze RDS MySQL instances and calculate Extended Support pricing costs for different years (1-3 years). This tool compares Extended Support costs with 1-year Reserved Instance pricing to help make cost-effective decisions for MySQL version lifecycle management. It provides detailed cost analysis including per-core pricing, total MRR calculations, and percentage comparisons between Extended Support and Reserved Instance options.",
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "AWS region for analysis (e.g., us-east-1, ap-northeast-1)"
                    },
                    "output_format": {
                        "type": "string",
                        "description": "Output format for results",
                        "enum": ["json", "csv", "markdown"],
                        "default": "json"
                    },
                },
                "required": ["region"]
            }
        ),
        Tool(
            name="run_mysql_sysbench_performance_test",
            description="Run sysbench performance tests on MySQL clusters. This tool executes comprehensive performance testing using sysbench to measure QPS (Queries Per Second), TPS (Transactions Per Second), and 95th percentile latency across different thread counts and scenarios. It supports multiple MySQL clusters, various test scenarios (oltp_read_write, oltp_read_only, etc.), and customizable test parameters. Results can be exported in JSON, CSV, or Markdown formats for analysis and reporting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "clusters": {
                        "type": "array",
                        "description": "List of MySQL cluster configurations to test",
                        "items": {
                            "type": "object",
                            "properties": {
                                "endpoint": {
                                    "type": "string",
                                    "description": "MySQL cluster endpoint hostname"
                                },
                                "port": {
                                    "type": "integer",
                                    "description": "MySQL port number",
                                    "default": 3306
                                },
                                "username": {
                                    "type": "string",
                                    "description": "MySQL username",
                                    "default": "admin"
                                },
                                "password": {
                                    "type": "string",
                                    "description": "MySQL password"
                                },
                                "database": {
                                    "type": "string",
                                    "description": "Database name for testing",
                                    "default": "sysbench_test"
                                },
                                "version": {
                                    "type": "string",
                                    "description": "MySQL/Aurora version for reporting"
                                },
                                "instance_size": {
                                    "type": "string",
                                    "description": "Instance size for reporting (e.g., r6g.2xlarge)"
                                }
                            },
                            "required": ["endpoint", "password", "version", "instance_size"]
                        }
                    },
                    "test_config": {
                        "type": "object",
                        "description": "Sysbench test configuration",
                        "properties": {
                            "table_count": {
                                "type": "integer",
                                "description": "Number of tables to create",
                                "default": 100
                            },
                            "table_size": {
                                "type": "integer",
                                "description": "Number of rows per table",
                                "default": 35000000
                            },
                            "test_duration": {
                                "type": "integer",
                                "description": "Test duration in seconds",
                                "default": 300
                            },
                            "scenarios": {
                                "type": "array",
                                "description": "List of test scenarios to run",
                                "items": {
                                    "type": "string",
                                    "enum": ["oltp_read_write", "oltp_read_only", "oltp_write_only", "oltp_point_select", "oltp_update_index", "oltp_update_non_index", "oltp_delete", "oltp_insert"]
                                },
                                "default": ["oltp_read_write"]
                            },
                            "thread_counts": {
                                "type": "array",
                                "description": "List of thread counts to test",
                                "items": {
                                    "type": "integer"
                                },
                                "default": [128, 256, 512]
                            }
                        }
                    },
                    "output_format": {
                        "type": "string",
                        "description": "Output format for results",
                        "enum": ["json", "csv", "markdown"],
                        "default": "json"
                    }
                },
                "required": ["clusters"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, args: dict) -> list[TextContent]:
    """Execute AWS RDS pricing analysis tools"""
    
    try:
        if name == "analyze_aurora_multi_generation_pricing":
            region = args.get("region")
            output_format = args.get("output_format", "json")
            
            if not region:
                raise ValueError("region parameter is required for Aurora multi-generation pricing analysis")
            
            logger.info(f"Starting Aurora multi-generation pricing analysis for region: {region}")
            
            # Create analyzer instance
            analyzer = RDSAuroraMultiGenerationPricingAnalyzer(region)
            
            # Execute analysis and export
            result_content = analyzer.analyze_and_export(output_format=output_format)
            
            if not result_content:
                return [TextContent(type="text", text="No RDS MySQL instances found in the specified region.")]
            
            # Return the content directly
            return [TextContent(type="text", text=result_content)]
                
        elif name == "analyze_mysql_extended_support_pricing":
            region = args.get("region")
            output_format = args.get("output_format", "json")
            
            if not region:
                raise ValueError("region parameter is required for MySQL Extended Support pricing analysis")
            
            logger.info(f"Starting MySQL Extended Support pricing analysis for region: {region}")
            
            # Create analyzer instance
            analyzer = RDSPricingAnalyzer(region)
            
            # Execute analysis and export
            result_content = analyzer.analyze_and_export(output_format=output_format)
            
            if not result_content:
                return [TextContent(type="text", text="No RDS MySQL instances found in the specified region.")]
            
            # Return the content directly
            return [TextContent(type="text", text=result_content)]
        
        elif name == "run_mysql_sysbench_performance_test":
            clusters_data = args.get("clusters", [])
            test_config_data = args.get("test_config", {})
            output_format = args.get("output_format", "json")
            
            if not clusters_data:
                raise ValueError("clusters parameter is required for sysbench performance testing")
            
            logger.info(f"Starting MySQL sysbench performance testing for {len(clusters_data)} cluster(s)")
            
            # Parse cluster configurations
            clusters = []
            for cluster_data in clusters_data:
                cluster = MySQLClusterConfig(
                    endpoint=cluster_data["endpoint"],
                    port=cluster_data.get("port", 3306),
                    username=cluster_data.get("username", "admin"),
                    password=cluster_data["password"],
                    database=cluster_data.get("database", "sysbench_test"),
                    version=cluster_data["version"],
                    instance_size=cluster_data["instance_size"]
                )
                clusters.append(cluster)
            
            # Parse test configuration
            test_config = SysbenchTestConfig(
                table_count=test_config_data.get("table_count", 100),
                table_size=test_config_data.get("table_size", 35000000),
                test_duration=test_config_data.get("test_duration", 300),
                scenarios=test_config_data.get("scenarios", ["oltp_read_write"]),
                thread_counts=test_config_data.get("thread_counts", [128, 256, 512])
            )
            
            # Create analyzer and run tests
            analyzer = MySQLSysbenchAnalyzer()
            
            try:
                results = analyzer.run_performance_tests(clusters, test_config)
                
                if not results:
                    return [TextContent(type="text", text="No test results were generated. Please check the cluster configurations and ensure sysbench and mysql client are installed.")]
                
                # Export results in the requested format
                if output_format == "csv":
                    result_content = analyzer.export_to_csv()
                elif output_format == "markdown":
                    result_content = analyzer.export_to_markdown()
                else:  # json
                    result_content = analyzer.export_to_json()
                
                return [TextContent(type="text", text=result_content)]
                
            except RuntimeError as e:
                error_message = f"Sysbench testing failed: {str(e)}"
                logger.error(error_message)
                return [TextContent(type="text", text=error_message)]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        error_message = f"Error executing tool '{name}': {str(e)}"
        logger.error(error_message)
        return [TextContent(type="text", text=error_message)]

@click.command()
@click.option("--transport", type=click.Choice(["stdio", "http"]), default="stdio", help="Transport type")
@click.option("--port", default=3000, help="Port to listen on for HTTP")
def run(transport: str, port: int) -> int:
    """Run the AWS RDS Pricing Analysis MCP Server"""
    
    if transport == 'stdio':
        from mcp.server.stdio import stdio_server

        async def arun():
            async with stdio_server() as (read_stream, write_stream):
                try:
                    logger.info("Starting AWS RDS Pricing Analysis MCP Server")
                    await server.run(
                        read_stream,
                        write_stream,
                        server.create_initialization_options()
                    )
                except Exception as e:
                    logger.warning(f"MCP Server Error: {str(e)}")
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
            async with session_manager.run():
                logger.info("Application started with StreamableHTTP session manager!")
                try:
                    yield
                finally:
                    logger.info("Application shutting down...")

        starlette_app = Starlette(
            routes=[
                Mount("/aws_rds_eval_mcp", app=handle_streamable_http),
                Route("/health", health, methods=["GET"])
            ],
            lifespan=lifespan
        )

        import uvicorn
        uvicorn.run(starlette_app, host="0.0.0.0", port=port)

    return 0

if __name__ == "__main__":
    run()
