import uuid
import json
import os
from datetime import datetime
from typing import List, Dict, Any

import boto3
from fastapi import HTTPException

from ..utils.aws_config import get_aws_region
from ..utils.pg_config import get_pg_connection

# EventBridge clients remain unchanged for PG backend
aws_region = get_aws_region()
_eventbridge = None

def _get_eventbridge():
    global _eventbridge
    if _eventbridge is None:
        _eventbridge = boto3.client('scheduler', region_name=aws_region)
    return _eventbridge

LAMBDA_FUNCTION_ARN = os.environ.get(
    'LAMBDA_FUNCTION_ARN',
    f"arn:aws:lambda:{aws_region}:719135481877:function:AgentXStack-AgentScheduleExecutorFunction-XXXXXXXXXXXX"
)
SCHEDULE_ROLE_ARN = os.environ.get(
    'SCHEDULE_ROLE_ARN',
    "arn:aws:iam::XXXXXXXXXXXX:role/EventBridgeSchedulerExecutionRole"
)


class PGScheduleService:
    """PostgreSQL implementation of schedule service.
    EventBridge calls are unchanged; only schedule metadata is stored in PG.
    """

    def list_schedules(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM agent_schedules WHERE user_id = %s",
                        (user_id,),
                    )
                    rows = cur.fetchall()
                    col_names = [desc[0] for desc in cur.description]
                    return [dict(zip(col_names, row)) for row in rows]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list schedules: {str(e)}")

    def create_schedule(
        self, agent_id: str, user_id: str, agent_user_id: str,
        cron_expression: str, user_message: str
    ) -> Dict[str, Any]:
        try:
            if not agent_id or not cron_expression:
                raise HTTPException(status_code=400, detail="Agent ID and cron expression are required")

            agent_name = self._get_agent_name(agent_id, agent_user_id)
            schedule_id = uuid.uuid4().hex
            current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            schedule_name = f"agent-schedule-{schedule_id}"
            eventbridge_cron = self._validate_cron_expression(cron_expression)

            _get_eventbridge().create_schedule(
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
                        "user_message": user_message,
                    }),
                },
                FlexibleTimeWindow={"Mode": "OFF"},
            )

            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO agent_schedules (user_id, id, agent_id, agent_user_id, agent_name,
                            cron_expression, status, eventbridge_schedule_name, created_at, updated_at, user_message)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            user_id, schedule_id, agent_id, agent_user_id, agent_name,
                            cron_expression, 'ENABLED', schedule_name,
                            current_time, current_time, user_message,
                        ),
                    )

            return {
                "user_id": user_id, "id": schedule_id, "agentId": agent_id,
                "agentUserId": agent_user_id, "agentName": agent_name,
                "cronExpression": cron_expression, "status": "ENABLED",
                "eventBridgeScheduleName": schedule_name,
                "createdAt": current_time, "updatedAt": current_time,
                "user_message": user_message,
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")

    def update_schedule(
        self, schedule_id: str, user_id: str, agent_id: str, agent_user_id: str,
        cron_expression: str, user_message: str
    ) -> Dict[str, Any]:
        try:
            if not agent_id or not cron_expression:
                raise HTTPException(status_code=400, detail="Agent ID and cron expression are required")

            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM agent_schedules WHERE user_id = %s AND id = %s",
                        (user_id, schedule_id),
                    )
                    row = cur.fetchone()
                    if not row:
                        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
                    col_names = [desc[0] for desc in cur.description]
                    schedule = dict(zip(col_names, row))

            eventbridge_schedule_name = schedule.get('eventbridge_schedule_name')
            agent_name = self._get_agent_name(agent_id, agent_user_id)
            eventbridge_cron = self._validate_cron_expression(cron_expression)
            current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

            _get_eventbridge().update_schedule(
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
                        "user_message": user_message,
                    }),
                },
                FlexibleTimeWindow={"Mode": "OFF"},
            )

            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE agent_schedules SET agent_id = %s, agent_user_id = %s, agent_name = %s,
                            cron_expression = %s, updated_at = %s, user_message = %s
                        WHERE user_id = %s AND id = %s
                        """,
                        (
                            agent_id, agent_user_id, agent_name,
                            cron_expression, current_time, user_message,
                            user_id, schedule_id,
                        ),
                    )

            return {
                "user_id": user_id, "id": schedule_id, "agentId": agent_id,
                "agentUserId": agent_user_id, "agentName": agent_name,
                "cronExpression": cron_expression, "status": schedule.get('status', 'ENABLED'),
                "eventBridgeScheduleName": eventbridge_schedule_name,
                "createdAt": schedule.get('created_at', current_time),
                "updatedAt": current_time, "user_message": user_message,
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update schedule: {str(e)}")

    def delete_schedule(self, schedule_id: str, user_id: str) -> Dict[str, Any]:
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM agent_schedules WHERE user_id = %s AND id = %s",
                        (user_id, schedule_id),
                    )
                    row = cur.fetchone()
                    if not row:
                        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
                    col_names = [desc[0] for desc in cur.description]
                    schedule = dict(zip(col_names, row))

            eventbridge_schedule_name = schedule.get('eventbridge_schedule_name')
            if eventbridge_schedule_name:
                _get_eventbridge().delete_schedule(Name=eventbridge_schedule_name)

            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM agent_schedules WHERE user_id = %s AND id = %s",
                        (user_id, schedule_id),
                    )

            return {"message": f"Schedule {schedule_id} deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete schedule: {str(e)}")

    def _get_agent_name(self, agent_id: str, agent_user_id: str) -> str:
        from ..utils.aws_config import get_dynamodb_resource
        dynamodb = get_dynamodb_resource()
        agent_table = dynamodb.Table("AgentTable")
        for key in [agent_user_id, 'public']:
            response = agent_table.get_item(Key={'user_id': key, 'id': agent_id})
            if 'Item' in response:
                return response['Item'].get('display_name', 'Unknown Agent')
        raise HTTPException(status_code=404, detail=f"Agent with ID {agent_id} not found")

    def _validate_cron_expression(self, cron_expression: str) -> str:
        cron_parts = cron_expression.split()
        if len(cron_parts) != 5:
            raise HTTPException(status_code=400, detail="Invalid cron expression format")
        if cron_parts[2] != '?' and cron_parts[4] != '?':
            raise HTTPException(
                status_code=400,
                detail="Either day-of-month or day-of-week must be '?' in EventBridge cron expressions",
            )
        return f"cron({cron_parts[0]} {cron_parts[1]} {cron_parts[2]} {cron_parts[3]} {cron_parts[4]} *)"
