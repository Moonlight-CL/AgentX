from .models import Schedule, ScheduleCreate
from ..storage.factory import get_schedule_service as _svc
from .service import get_agent_name, validate_cron_expression


def list_schedules(user_id):
    return _svc().list_schedules(user_id)


def create_schedule(agent_id, user_id, agent_user_id, cron_expression, user_message):
    return _svc().create_schedule(agent_id, user_id, agent_user_id, cron_expression, user_message)


def update_schedule(schedule_id, user_id, agent_id, agent_user_id, cron_expression, user_message):
    return _svc().update_schedule(schedule_id, user_id, agent_id, agent_user_id, cron_expression, user_message)


def delete_schedule(schedule_id, user_id):
    return _svc().delete_schedule(schedule_id, user_id)


__all__ = [
    'Schedule', 'ScheduleCreate',
    'list_schedules', 'create_schedule',
    'update_schedule', 'delete_schedule',
    'get_agent_name', 'validate_cron_expression',
]
