from collections.abc import AsyncIterator
import logging
import os
import asyncio
import anyio
import boto3
import json
import click
import csv
import io
from typing import Dict, List
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import Tool, TextContent
from pydantic import AnyUrl

# Import the RDS Aurora pricing analyzer
from .rds_aurora_pricing_analyzer import RDSAuroraMultiGenerationPricingAnalyzer

# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('aws_db_evaluation_mcp_log.out')
    ]
)
logger = logging.getLogger('aws-db-evaluation-mcp-server')

aws_db_scheme = "aws-db://"
mime_txt = "text/plain"
mime_csv = "text/csv"
mime_json = "application/json"

# Initialize MCP Server
server = Server("aws-db-evaluation-mcp-server")
server.version = "0.1.0"

def get_aws_config() -> dict[str, str]:
    """Get AWS configuration from environment variables."""
    config = {
        "region": os.getenv("AWS_REGION", "us-west-2"),
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "aws_session_token": os.getenv("AWS_SESSION_TOKEN")
    }
    return config

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available AWS DB evaluation tools"""
    logger.info("List available tools...")

    return [
        Tool(
            name="analyze_rds_instances",
            description="Analyze RDS MySQL instances and calculate Aurora conversion and RDS replacement costs",
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "AWS region (e.g., us-east-1)"
                    },
                    "output_format": {
                        "type": "string",
                        "description": "Output format (json or csv)",
                        "enum": ["json", "csv"],
                        "default": "json"
                    }
                },
                "required": ["region"]
            }
        ),
        Tool(
            name="get_instance_pricing",
            description="Get pricing information for specific RDS and Aurora instance types",
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "AWS region (e.g., us-east-1)"
                    },
                    "instance_class": {
                        "type": "string",
                        "description": "RDS instance class (e.g., db.r5.xlarge)"
                    },
                    "aurora_generations": {
                        "type": "array",
                        "description": "Aurora instance generations to check (e.g., r7g, r8g)",
                        "items": {
                            "type": "string"
                        },
                        "default": ["r7g", "r8g"]
                    }
                },
                "required": ["region", "instance_class"]
            }
        ),
        Tool(
            name="calculate_storage_cost",
            description="Calculate storage costs for RDS and Aurora",
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "AWS region (e.g., us-east-1)"
                    },
                    "storage_type": {
                        "type": "string",
                        "description": "Storage type (gp2, gp3, io1, io2, magnetic)",
                        "enum": ["gp2", "gp3", "io1", "io2", "magnetic"]
                    },
                    "allocated_storage_gb": {
                        "type": "number",
                        "description": "Allocated storage in GB"
                    },
                    "iops": {
                        "type": "number",
                        "description": "Provisioned IOPS (for io1, io2, gp3)",
                        "default": 0
                    },
                    "throughput_mbps": {
                        "type": "number",
                        "description": "Provisioned throughput in MB/s (for gp3)",
                        "default": 0
                    },
                    "is_multi_az": {
                        "type": "boolean",
                        "description": "Whether the instance is Multi-AZ",
                        "default": False
                    },
                    "is_aurora_migration": {
                        "type": "boolean",
                        "description": "Whether this is for Aurora migration calculation",
                        "default": False
                    }
                },
                "required": ["region", "storage_type", "allocated_storage_gb"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, args: dict) -> list[TextContent]:
    """Execute AWS DB evaluation tools"""
    # config = get_aws_config()
    
    try:
        if name == "analyze_rds_instances":
            region = args.get("region")
            output_format = args.get("output_format", "json")
            
            if not region:
                raise ValueError("region parameter is required when calling analyze_rds_instances tool")
            
            # Create analyzer instance
            analyzer = RDSAuroraMultiGenerationPricingAnalyzer(region)
            
            # Analyze instances
            results = analyzer.analyze_instances()
            
            if output_format == "csv":
                # Convert results to CSV
                output = _convert_to_csv(results)
                return [TextContent(type="text", text=output)]
            else:
                # Return JSON results
                return [TextContent(type="text", text=json.dumps(results, default=str, indent=2))]
                
        elif name == "get_instance_pricing":
            region = args.get("region")
            instance_class = args.get("instance_class")
            aurora_generations = args.get("aurora_generations", ["r7g", "r8g"])
            
            if not all([region, instance_class]):
                raise ValueError("region and instance_class parameters are required when calling get_instance_pricing tool")
            
            # Create analyzer instance
            analyzer = RDSAuroraMultiGenerationPricingAnalyzer(region)
            
            # Get RDS MySQL pricing
            analyzer.get_rds_mysql_pricing()
            rds_hourly_rate = analyzer.get_instance_pricing_from_cache(instance_class)
            rds_mrr = analyzer.calculate_mrr(rds_hourly_rate) if rds_hourly_rate else None
            
            # Get Aurora pricing for each generation
            aurora_pricing = {}
            for generation in aurora_generations:
                aurora_instance_class = analyzer.map_to_aurora_instance(instance_class, generation)
                aurora_hourly_rate = analyzer.get_aurora_mysql_pricing(aurora_instance_class)
                aurora_mrr = analyzer.calculate_mrr(aurora_hourly_rate) if aurora_hourly_rate else None
                
                aurora_pricing[generation] = {
                    "instance_class": aurora_instance_class,
                    "hourly_rate_usd": aurora_hourly_rate,
                    "mrr_usd": aurora_mrr
                }
            
            # Prepare results
            pricing_info = {
                "rds_instance_class": instance_class,
                "rds_hourly_rate_usd": rds_hourly_rate,
                "rds_mrr_usd": rds_mrr,
                "aurora_pricing": aurora_pricing
            }
            
            return [TextContent(type="text", text=json.dumps(pricing_info, default=str, indent=2))]
            
        elif name == "calculate_storage_cost":
            region = args.get("region")
            storage_type = args.get("storage_type")
            allocated_storage_gb = args.get("allocated_storage_gb")
            iops = args.get("iops", 0)
            throughput_mbps = args.get("throughput_mbps", 0)
            is_multi_az = args.get("is_multi_az", False)
            is_aurora_migration = args.get("is_aurora_migration", False)
            
            if not all([region, storage_type, allocated_storage_gb is not None]):
                raise ValueError("region, storage_type, and allocated_storage_gb parameters are required when calling calculate_storage_cost tool")
            
            # Create analyzer instance
            analyzer = RDSAuroraMultiGenerationPricingAnalyzer(region)
            
            # Get storage pricing
            analyzer.get_all_storage_pricing()
            storage_pricing = analyzer.get_storage_pricing(storage_type)
            
            # Calculate RDS storage cost
            storage_info = {
                "storage_type": storage_type,
                "allocated_storage_gb": allocated_storage_gb,
                "iops": iops,
                "storage_throughput_mbps": throughput_mbps
            }
            
            rds_storage_cost = analyzer.calculate_storage_cost(
                storage_info, 
                storage_pricing, 
                is_multi_az, 
                is_aurora_migration=False
            )
            
            # Calculate Aurora storage cost if requested
            aurora_storage_cost = None
            if is_aurora_migration:
                # Get Aurora storage pricing
                aurora_storage_pricing = analyzer.get_aurora_storage_pricing()
                
                # Calculate Aurora storage cost based on used storage
                aurora_storage_gb = allocated_storage_gb  # Using allocated storage as an approximation
                aurora_storage_price = aurora_storage_pricing.get("storage_price_per_gb_month", 0)
                aurora_storage_cost_per_month = aurora_storage_gb * aurora_storage_price
                
                aurora_storage_cost = {
                    "aurora_storage_gb": aurora_storage_gb,
                    "aurora_storage_price_per_gb_month_usd": aurora_storage_price,
                    "aurora_total_storage_cost_per_month_usd": aurora_storage_cost_per_month
                }
            
            # Prepare results
            cost_info = {
                "rds_storage_cost": rds_storage_cost,
                "aurora_storage_cost": aurora_storage_cost
            }
            
            return [TextContent(type="text", text=json.dumps(cost_info, default=str, indent=2))]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error executing tool: {str(e)}")]

def _get_aws_regions() -> str:
    """Get list of AWS regions"""
    regions = [
        "us-east-1", "us-east-2", "us-west-1", "us-west-2",
        "ap-east-1", "ap-south-1", "ap-south-2", "ap-northeast-1",
        "ap-northeast-2", "ap-northeast-3", "ap-southeast-1", "ap-southeast-2",
        "ap-southeast-3", "ap-southeast-4", "ca-central-1", "eu-central-1",
        "eu-central-2", "eu-west-1", "eu-west-2", "eu-west-3", "eu-north-1",
        "eu-south-1", "eu-south-2", "me-south-1", "me-central-1", "af-south-1",
        "sa-east-1"
    ]
    return "\n".join(regions)

def _get_supported_generations() -> str:
    """Get supported instance generations for Aurora and RDS replacement"""
    generations = {
        "aurora_generations": ["r7g", "r8g"],
        "rds_replacement_generations": ["r7g", "r8g"]
    }
    return json.dumps(generations, indent=2)

def _convert_to_csv(data: List[Dict]) -> str:
    """Convert list of dictionaries to CSV string"""
    if not data:
        return ""
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    
    return output.getvalue()

@click.command()
@click.option("--transport",  type=click.Choice(["stdio", "http"]), default="stdio", help="Transport type",)
@click.option("--port", default=3001, help="Port to listen on for HTTP")
# @click.option("--env_file", default=".env", help="AWS DB evaluation MCP env file path")
def run(transport: str, port: int) -> int:
    if transport == 'stdio':
        from mcp.server.stdio import stdio_server

        async def arun():
            async with stdio_server() as (read_stream, write_stream):
                try:
                    logger.info("Starting AWS DB evaluation MCP Server")
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
        from dotenv import load_dotenv
        import contextlib

        # load_dotenv(dotenv_path=env_file)

        async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
            await session_manager.handle_request(scope, receive, send)

        async def health(request):
            return JSONResponse({'status': 'healthy'})

        @contextlib.asynccontextmanager
        async def lifespan(app: Starlette) -> AsyncIterator[None]:
            """Context Manager for Session Manager"""
            async with session_manager.run():
                logger.info("Application started with StreamableHTTP session manager!")
                try:
                    yield
                finally:
                    logger.info("Application shutting down...")

        starlette_app = Starlette(
            routes=[
                Mount("/aws_db_mcp", app=handle_streamable_http),
                Route("/health", health, methods=["GET"])
            ],
            lifespan=lifespan
        )

        import uvicorn

        uvicorn.run(starlette_app, host="0.0.0.0", port=port)

    return 0

if __name__ == "__main__":
    run()
