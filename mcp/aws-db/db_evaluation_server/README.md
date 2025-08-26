# AWS DB Evaluation MCP Server

This MCP (Model Context Protocol) server provides tools for analyzing RDS MySQL instances and calculating Aurora conversion and RDS replacement costs. It leverages the functionality from the `RDSAuroraMultiGenerationPricingAnalyzer` to provide pricing analysis through MCP tools and resources.

## Features

- Analyze RDS MySQL instances and calculate Aurora conversion costs
- Calculate RDS replacement costs with newer generation instances (r7g, r8g)
- Get pricing information for specific RDS and Aurora instance types
- Calculate storage costs for different storage types and configurations
- Support for Multi-AZ and TAZ (Three Availability Zone) architectures
- Support for RDS MySQL clusters and Aurora clusters

## Resources

The server provides the following resources:

- `aws-db://regions` - List all AWS regions
- `aws-db://supported-generations` - List supported instance generations for Aurora and RDS replacement
- `aws-db://{region}/rds-instances` - List all RDS MySQL instances in a region
- `aws-db://{region}/aurora-clusters` - List all Aurora MySQL clusters in a region
- `aws-db://{region}/storage-pricing` - Get storage pricing information for a region

## Tools

The server provides the following tools:

### analyze_rds_instances

Analyze RDS MySQL instances and calculate Aurora conversion and RDS replacement costs.

**Parameters:**
- `region` (required): AWS region (e.g., us-east-1)
- `output_format` (optional): Output format (json or csv), default is json

**Example:**
```json
{
  "region": "us-east-1",
  "output_format": "json"
}
```

### get_instance_pricing

Get pricing information for specific RDS and Aurora instance types.

**Parameters:**
- `region` (required): AWS region (e.g., us-east-1)
- `instance_class` (required): RDS instance class (e.g., db.r5.xlarge)
- `aurora_generations` (optional): Aurora instance generations to check (e.g., r7g, r8g), default is ["r7g", "r8g"]

**Example:**
```json
{
  "region": "us-east-1",
  "instance_class": "db.r5.xlarge",
  "aurora_generations": ["r7g", "r8g"]
}
```

### calculate_storage_cost

Calculate storage costs for RDS and Aurora.

**Parameters:**
- `region` (required): AWS region (e.g., us-east-1)
- `storage_type` (required): Storage type (gp2, gp3, io1, io2, magnetic)
- `allocated_storage_gb` (required): Allocated storage in GB
- `iops` (optional): Provisioned IOPS (for io1, io2, gp3), default is 0
- `throughput_mbps` (optional): Provisioned throughput in MB/s (for gp3), default is 0
- `is_multi_az` (optional): Whether the instance is Multi-AZ, default is false
- `is_aurora_migration` (optional): Whether this is for Aurora migration calculation, default is false

**Example:**
```json
{
  "region": "us-east-1",
  "storage_type": "gp3",
  "allocated_storage_gb": 100,
  "iops": 3000,
  "throughput_mbps": 125,
  "is_multi_az": true,
  "is_aurora_migration": true
}
```

## Running the Server

### Prerequisites

- Python 3.8+
- AWS credentials configured (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION)
- Required Python packages: boto3, mcp, anyio, click, starlette, uvicorn

### Starting the Server

You can run the server using either stdio or HTTP transport:

#### Using stdio (default)

```bash
python -m db_evaluation_server
```

#### Using HTTP

```bash
python -m db_evaluation_server --transport http --port 3001
```

### Environment Variables

The server uses the following environment variables:

- `AWS_REGION`: AWS region (default: us-east-1)
- `AWS_ACCESS_KEY_ID`: AWS access key ID
- `AWS_SECRET_ACCESS_KEY`: AWS secret access key
- `AWS_SESSION_TOKEN`: AWS session token (optional)

You can set these variables in a `.env` file and specify the path using the `--env_file` option:

```bash
python -m db_evaluation_server --env_file /path/to/.env
```

## Testing

You can test the server functionality using the provided test script:

```bash
python test_db_evaluation_server.py --region us-east-1
```

This script tests the core functionality of the RDS Aurora pricing analyzer without requiring the MCP server to be running.
