# AWS RDS Pricing Analysis MCP Server

This MCP server provides comprehensive pricing analysis tools for AWS RDS MySQL instances, including Aurora migration cost analysis and Extended Support pricing evaluation.

## Features

### 1. Aurora Multi-Generation Pricing Analysis
- **Tool Name**: `analyze_aurora_multi_generation_pricing`
- **Description**: Analyzes RDS MySQL instances and calculates Aurora conversion costs with multi-generation support (r7g, r8g)
- **Key Features**:
  - Comprehensive pricing analysis including instance costs, storage costs, and total MRR
  - Support for various architectures: Single-AZ, Multi-AZ, TAZ clusters, and RDS MySQL clusters
  - Analysis includes both Aurora Standard and IO Optimized configurations
  - CloudWatch metrics integration for accurate IO cost calculations
  - Support for M/R/C series instances with intelligent mapping to Aurora R-series
  - RDS replacement cost analysis with Graviton3/4 migration options

### 2. MySQL Extended Support Pricing Analysis
- **Tool Name**: `analyze_mysql_extended_support_pricing`
- **Description**: Analyzes RDS MySQL instances and calculates Extended Support pricing costs for different years (1-3 years)
- **Key Features**:
  - Compares Extended Support costs with 1-year Reserved Instance pricing
  - Detailed cost analysis including per-core pricing and total MRR calculations
  - Percentage comparisons between Extended Support and Reserved Instance options
  - Support for Multi-AZ cost adjustments

## Installation

1. Ensure you have the required dependencies installed:
```bash
pip install mcp boto3 click anyio starlette uvicorn pandas openpyxl
```

2. Set up AWS credentials with appropriate permissions for:
   - RDS instance discovery (`rds:DescribeDBInstances`, `rds:DescribeDBClusters`)
   - CloudWatch metrics access (`cloudwatch:GetMetricStatistics`)
   - Pricing API access (`pricing:GetProducts`)

## Usage

### Running the Server

#### STDIO Transport (Default)
```bash
python -m mcp.aws-db.db_evaluation_server.pricing_analysis_server
```

#### HTTP Transport
```bash
python -m mcp.aws-db.db_evaluation_server.pricing_analysis_server --transport http --port 3002
```

### Tool Parameters

#### analyze_aurora_multi_generation_pricing
- **region** (required): AWS region for analysis (e.g., "us-east-1", "ap-northeast-1")
- **output_format** (optional): Output format - "json", "csv", or "markdown" (default: "json")
- **output_file** (optional): Custom output file path (auto-generated if not provided)

#### analyze_mysql_extended_support_pricing
- **region** (required): AWS region for analysis (e.g., "us-east-1", "ap-northeast-1")
- **output_format** (optional): Output format - "json", "csv", or "markdown" (default: "json")
- **output_file** (optional): Custom output file path (auto-generated if not provided)

### Example Usage with MCP Client

```python
# Aurora Multi-Generation Analysis
result = await mcp_client.call_tool(
    "analyze_aurora_multi_generation_pricing",
    {
        "region": "us-east-1",
        "output_format": "json"
    }
)

# Extended Support Analysis
result = await mcp_client.call_tool(
    "analyze_mysql_extended_support_pricing",
    {
        "region": "ap-northeast-1",
        "output_format": "csv",
        "output_file": "extended_support_analysis.csv"
    }
)
```

## Output Formats

### JSON Format
Returns detailed analysis results as structured JSON data, suitable for programmatic processing.

### CSV Format
Exports results to Excel files (.xlsx) with multiple sheets:
- **详细数据**: Complete instance-level analysis
- **cluster成本汇总**: Cluster-level cost summaries

### Markdown Format
Generates human-readable reports with:
- Executive summary tables
- Detailed instance analysis
- Cost comparison charts

## Architecture Support

### Aurora Multi-Generation Analysis
- **Single-AZ**: Standard single availability zone instances
- **Multi-AZ**: Multi availability zone deployments
- **TAZ Clusters**: Three availability zone Aurora clusters
- **RDS MySQL Clusters**: Read replica configurations

### Instance Type Support
- **M-Series**: General purpose instances (mapped to Aurora R-series)
- **R-Series**: Memory optimized instances
- **C-Series**: Compute optimized instances (mapped to Aurora R-series)

### Migration Scenarios
1. **Aurora Migration**: All instance types → Aurora r7g/r8g
2. **Graviton Migration**: 
   - M/C series → m7g/m8g
   - R series → r7g/r8g

## Cost Calculations

### Aurora Analysis
- **Instance MRR**: Monthly recurring revenue for Aurora instances
- **Storage MRR**: Aurora storage costs based on actual usage
- **IO MRR**: Aurora IO costs based on CloudWatch IOPS metrics
- **Total MRR**: Combined instance + storage + IO costs
- **Standard vs Optimized**: Both Aurora configurations analyzed

### Extended Support Analysis
- **Per-Core Pricing**: Extended Support costs calculated per CPU core
- **Multi-AZ Adjustments**: Automatic cost doubling for Multi-AZ deployments
- **Year-over-Year Analysis**: 1-3 year Extended Support cost projections
- **RI Comparison**: Percentage difference vs Reserved Instance pricing

## Logging

The server generates detailed logs in `aws_rds_pricing_analysis_mcp_log.out` including:
- Analysis progress and timing
- API call results and caching
- Error handling and debugging information
- Cost calculation details

## Error Handling

The server includes comprehensive error handling for:
- Invalid AWS regions
- Missing AWS credentials
- API rate limiting and throttling
- Instance type mapping failures
- Pricing data unavailability

## Performance Optimization

- **Caching**: Extensive caching of pricing data and instance information
- **Batch Processing**: Efficient bulk API calls for large instance sets
- **Parallel Analysis**: Concurrent processing of multiple instances
- **Smart Filtering**: Automatic filtering of unsupported instance types

## Security Considerations

- Uses AWS SDK credential chain for secure authentication
- No sensitive data stored in logs or output files
- Supports IAM role-based access control
- Minimal required permissions for operation

## Troubleshooting

### Common Issues

1. **No instances found**: Verify region parameter and AWS credentials
2. **Pricing data unavailable**: Check internet connectivity and AWS Pricing API access
3. **Permission errors**: Ensure IAM permissions for RDS, CloudWatch, and Pricing APIs
4. **Memory issues**: For large instance sets, consider processing by region

### Debug Mode

Enable detailed logging by setting the log level to DEBUG in the server configuration.

## Contributing

When extending the server:
1. Follow the existing code structure and patterns
2. Add comprehensive error handling
3. Include detailed logging for debugging
4. Update this README with new features
5. Test with various AWS regions and instance configurations
