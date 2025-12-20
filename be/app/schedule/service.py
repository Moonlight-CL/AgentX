import uuid
import json
import os
from datetime import datetime
import boto3
from typing import List, Dict, Any, Optional
from fastapi import HTTPException

from .models import Schedule, ScheduleCreate
from ..utils.aws_config import get_aws_region

# Initialize AWS clients
aws_region = get_aws_region()
eventbridge = boto3.client('scheduler', region_name=aws_region)
dynamodb = boto3.resource('dynamodb', region_name=aws_region)

# DynamoDB table name
SCHEDULE_TABLE_NAME = "AgentScheduleTable"

# Lambda function ARN and role ARN from environment variables
aws_region = get_aws_region()
LAMBDA_FUNCTION_ARN = os.environ.get('LAMBDA_FUNCTION_ARN', f"arn:aws:lambda:{aws_region}:719135481877:function:AgentXStack-AgentScheduleExecutorFunction-XXXXXXXXXXXX")
SCHEDULE_ROLE_ARN = os.environ.get('SCHEDULE_ROLE_ARN', "arn:aws:iam::XXXXXXXXXXXX:role/EventBridgeSchedulerExecutionRole")


def list_schedules(user_id: str) -> List[Dict[str, Any]]:
    """
    List all agent schedules for a specific user.
    :param user_id: The ID of the user.
    :return: A list of schedules.
    """
    try:
        table = dynamodb.Table(SCHEDULE_TABLE_NAME)
        response = table.query(
            KeyConditionExpression='user_id = :user_id',
            ExpressionAttributeValues={
                ':user_id': user_id
            }
        )
        items = response.get('Items', [])
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list schedules: {str(e)}")


def get_agent_name(agent_id: str, agent_user_id: str) -> str:
    """
    Get the agent name from the agent table.
    :param agent_id: The ID of the agent.
    :param agent_user_id: The user ID of the agent owner.
    :return: The agent name.
    """
    agent_table = dynamodb.Table("AgentTable")
    
    # Try with provided agent_user_id first
    keys_to_try = [agent_user_id, 'public']
    
    for key in keys_to_try:
        agent_response = agent_table.get_item(Key={'user_id': key, 'id': agent_id})
        if 'Item' in agent_response:
            return agent_response['Item'].get('display_name', 'Unknown Agent')
    
    raise HTTPException(status_code=404, detail=f"Agent with ID {agent_id} not found")


def validate_cron_expression(cron_expression: str) -> str:
    """
    Validate and convert cron expression to EventBridge format.
    :param cron_expression: The cron expression to validate.
    :return: The EventBridge cron expression.
    """
    cron_parts = cron_expression.split()
    if len(cron_parts) != 5:
        raise HTTPException(status_code=400, detail="Invalid cron expression format")
    
    # Validate that either day-of-month or day-of-week is '?'
    if cron_parts[2] != '?' and cron_parts[4] != '?':
        raise HTTPException(
            status_code=400, 
            detail="Either day-of-month or day-of-week must be '?' in EventBridge cron expressions"
        )
    
    return f"cron({cron_parts[0]} {cron_parts[1]} {cron_parts[2]} {cron_parts[3]} {cron_parts[4]} *)"


def create_schedule(agent_id: str, user_id: str, agent_user_id: str, cron_expression: str, user_message: str) -> Dict[str, Any]:
    """
    Create a new agent schedule.
    :param agent_id: The ID of the agent.
    :param user_id: The ID of the user creating the schedule.
    :param agent_user_id: The user ID of the agent owner.
    :param cron_expression: The cron expression for the schedule.
    :param user_message: The message to send to the agent when the schedule is triggered.
    :return: The created schedule.
    """
    try:
        if not agent_id or not cron_expression:
            raise HTTPException(status_code=400, detail="Agent ID and cron expression are required")
        
        # Get agent name
        agent_name = get_agent_name(agent_id, agent_user_id)
        
        # Generate a unique ID for the schedule
        schedule_id = uuid.uuid4().hex
        current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Create EventBridge schedule
        schedule_name = f"agent-schedule-{schedule_id}"
        
        # Validate and convert cron expression
        eventbridge_cron = validate_cron_expression(cron_expression)
        
        # Create the schedule in EventBridge
        eventbridge_response = eventbridge.create_schedule(
            Name=schedule_name,
            ScheduleExpression=eventbridge_cron,
            State="ENABLED",
            Target={
                "Arn": LAMBDA_FUNCTION_ARN,
                "RoleArn": SCHEDULE_ROLE_ARN,
                "Input": json.dumps({
                    "user_id": user_id,
                    "agent_id": agent_id,
                    "agent_owner_id": agent_user_id,
                    "schedule_id": schedule_id,
                    "user_message": user_message
                })
            },
            FlexibleTimeWindow={
                "Mode": "OFF"
            }
        )
        
        # Store the schedule in DynamoDB with composite key
        schedule_item = {
            "user_id": user_id,
            "id": schedule_id,
            "agentId": agent_id,
            "agentUserId": agent_user_id,
            "agentName": agent_name,
            "cronExpression": cron_expression,
            "status": "ENABLED",
            "eventBridgeScheduleName": schedule_name,
            "createdAt": current_time,
            "updatedAt": current_time,
            "user_message": user_message
        }
        
        table = dynamodb.Table(SCHEDULE_TABLE_NAME)
        table.put_item(Item=schedule_item)
        
        return schedule_item
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")


def update_schedule(schedule_id: str, user_id: str, agent_id: str, agent_user_id: str, cron_expression: str, user_message: str) -> Dict[str, Any]:
    """
    Update a specific schedule by ID.
    :param schedule_id: The ID of the schedule to update.
    :param user_id: The ID of the user who owns the schedule.
    :param agent_id: The ID of the agent.
    :param agent_user_id: The user ID of the agent owner.
    :param cron_expression: The cron expression for the schedule.
    :param user_message: The message to send to the agent when the schedule is triggered.
    :return: The updated schedule.
    """
    try:
        if not agent_id or not cron_expression:
            raise HTTPException(status_code=400, detail="Agent ID and cron expression are required")
        
        # Get the schedule from DynamoDB using composite key
        table = dynamodb.Table(SCHEDULE_TABLE_NAME)
        response = table.get_item(Key={"user_id": user_id, "id": schedule_id})
        
        if "Item" not in response:
            raise HTTPException(status_code=404, detail=f"Schedule with ID {schedule_id} not found")
        
        schedule = response["Item"]
        eventbridge_schedule_name = schedule.get("eventBridgeScheduleName")
        
        # Get agent name
        agent_name = get_agent_name(agent_id, agent_user_id)
        
        # Validate and convert cron expression
        eventbridge_cron = validate_cron_expression(cron_expression)
        
        # Update the schedule in EventBridge
        eventbridge.update_schedule(
            Name=eventbridge_schedule_name,
            ScheduleExpression=eventbridge_cron,
            Target={
                "Arn": LAMBDA_FUNCTION_ARN,
                "RoleArn": SCHEDULE_ROLE_ARN,
                "Input": json.dumps({
                    "user_id": user_id,
                    "agent_id": agent_id,
                    "agent_owner_id": agent_user_id,
                    "schedule_id": schedule_id,
                    "user_message": user_message
                })
            },
            FlexibleTimeWindow={
                "Mode": "OFF"
            }
        )
        
        # Update the schedule in DynamoDB with composite key
        current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        updated_schedule = {
            "user_id": user_id,
            "id": schedule_id,
            "agentId": agent_id,
            "agentUserId": agent_user_id,
            "agentName": agent_name,
            "cronExpression": cron_expression,
            "status": schedule.get("status", "ENABLED"),
            "eventBridgeScheduleName": eventbridge_schedule_name,
            "createdAt": schedule.get("createdAt", current_time),
            "updatedAt": current_time,
            "user_message": user_message
        }
        
        table.put_item(Item=updated_schedule)
        
        return updated_schedule
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {str(e)}")


def delete_schedule(schedule_id: str, user_id: str) -> Dict[str, Any]:
    """
    Delete a specific schedule by ID.
    :param schedule_id: The ID of the schedule to delete.
    :param user_id: The ID of the user who owns the schedule.
    :return: Confirmation of deletion.
    """
    try:
        # Get the schedule from DynamoDB using composite key
        table = dynamodb.Table(SCHEDULE_TABLE_NAME)
        response = table.get_item(Key={"user_id": user_id, "id": schedule_id})
        
        if "Item" not in response:
            raise HTTPException(status_code=404, detail=f"Schedule with ID {schedule_id} not found")
        
        schedule = response["Item"]
        eventbridge_schedule_name = schedule.get("eventBridgeScheduleName")
        
        # Delete the schedule from EventBridge
        if eventbridge_schedule_name:
            eventbridge.delete_schedule(Name=eventbridge_schedule_name)
        
        # Delete the schedule from DynamoDB using composite key
        table.delete_item(Key={"user_id": user_id, "id": schedule_id})
        
        return {"message": f"Schedule {schedule_id} deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete schedule: {str(e)}")
