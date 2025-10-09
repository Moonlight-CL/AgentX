import os
import boto3
from typing import Dict, Any

def get_aws_region():
    """
    Get the AWS region from environment variables with a fallback to a default value.
    
    Returns:
        str: The AWS region to use for AWS services.
    """
    return os.environ.get('AWS_REGION', 'us-west-2')

# Global DynamoDB resource instance
_dynamodb_resource = None

def get_dynamodb_resource():
    """
    Get a shared DynamoDB resource instance.
    
    Returns:
        boto3.resource: The DynamoDB resource instance.
    """
    global _dynamodb_resource
    if _dynamodb_resource is None:
        aws_region = get_aws_region()
        _dynamodb_resource = boto3.resource('dynamodb', region_name=aws_region)
    return _dynamodb_resource

def get_dynamodb_table(table_name: str):
    """
    Get a DynamoDB table instance.
    
    Args:
        table_name (str): The name of the DynamoDB table.
        
    Returns:
        boto3.resource.Table: The DynamoDB table instance.
    """
    dynamodb = get_dynamodb_resource()
    return dynamodb.Table(table_name)

# Table name constants for centralized management
class DynamoDBTables:
    """Centralized DynamoDB table name constants."""
    
    # Agent related tables
    AGENTS = "AgentTable"
    CHAT_RECORDS = "ChatRecordTable"
    CHAT_RESPONSES = "ChatResponseTable"
    
    # User related tables
    USERS = "UserTable"
    
    # MCP related tables
    HTTP_MCP_SERVERS = "HttpMCPTable"
    
    # Schedule related tables
    AGENT_SCHEDULES = "AgentScheduleTable"
    
    # Orchestration related tables
    ORCHESTRATIONS = "OrcheTable"
    ORCHESTRATION_EXECUTIONS = "OrcheExecTable"
    
    # Configuration related tables
    CONFIGURATIONS = "ConfTable"

def get_agent_table():
    """Get the agents DynamoDB table."""
    return get_dynamodb_table(DynamoDBTables.AGENTS)

def get_chat_record_table():
    """Get the chat records DynamoDB table."""
    return get_dynamodb_table(DynamoDBTables.CHAT_RECORDS)

def get_chat_response_table():
    """Get the chat responses DynamoDB table."""
    return get_dynamodb_table(DynamoDBTables.CHAT_RESPONSES)

def get_user_table():
    """Get the users DynamoDB table."""
    return get_dynamodb_table(DynamoDBTables.USERS)

def get_http_mcp_table():
    """Get the HTTP MCP servers DynamoDB table."""
    return get_dynamodb_table(DynamoDBTables.HTTP_MCP_SERVERS)

def get_schedule_table():
    """Get the agent schedules DynamoDB table."""
    return get_dynamodb_table(DynamoDBTables.AGENT_SCHEDULES)

def get_orchestration_table():
    """Get the orchestrations DynamoDB table."""
    return get_dynamodb_table(DynamoDBTables.ORCHESTRATIONS)

def get_orchestration_execution_table():
    """Get the orchestration executions DynamoDB table."""
    return get_dynamodb_table(DynamoDBTables.ORCHESTRATION_EXECUTIONS)

def get_config_table():
    """Get the configurations DynamoDB table."""
    return get_dynamodb_table(DynamoDBTables.CONFIGURATIONS)
