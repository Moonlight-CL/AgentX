from .service import (
    list_schedules as _list,
    create_schedule as _create,
    update_schedule as _update,
    delete_schedule as _delete,
)


class DynamoDBScheduleService:
    """Wraps module-level DynamoDB schedule functions as a class."""

    def list_schedules(self, user_id):
        return _list(user_id)

    def create_schedule(self, agent_id, user_id, agent_user_id, cron_expression, user_message):
        return _create(agent_id, user_id, agent_user_id, cron_expression, user_message)

    def update_schedule(self, schedule_id, user_id, agent_id, agent_user_id, cron_expression, user_message):
        return _update(schedule_id, user_id, agent_id, agent_user_id, cron_expression, user_message)

    def delete_schedule(self, schedule_id, user_id):
        return _delete(schedule_id, user_id)
