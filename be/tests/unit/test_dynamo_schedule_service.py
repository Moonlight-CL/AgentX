"""
Unit tests for app/schedule/dynamo_schedule_service.py — DynamoDBScheduleService.

DynamoDBScheduleService is a thin wrapper that delegates to module-level
functions imported from app.schedule.service:

    _list, _create, _update, _delete

Each test patches the corresponding module-level function and verifies that
DynamoDBScheduleService passes the correct arguments through unchanged.
"""
import pytest
from unittest.mock import MagicMock, patch, call

from app.schedule.dynamo_schedule_service import DynamoDBScheduleService  # type: ignore


# ---------------------------------------------------------------------------
# Module-level function paths (as imported inside dynamo_schedule_service.py)
# ---------------------------------------------------------------------------

_MOD = 'app.schedule.dynamo_schedule_service'
PATCH_LIST   = f'{_MOD}._list'
PATCH_CREATE = f'{_MOD}._create'
PATCH_UPDATE = f'{_MOD}._update'
PATCH_DELETE = f'{_MOD}._delete'


# ---------------------------------------------------------------------------
# list_schedules
# ---------------------------------------------------------------------------

def test_list_schedules_delegates():
    mock_list = MagicMock(return_value=[{'id': 'sched1'}])
    with patch(PATCH_LIST, mock_list):
        svc = DynamoDBScheduleService()
        result = svc.list_schedules('user-42')
    mock_list.assert_called_once_with('user-42')
    assert result == [{'id': 'sched1'}]


def test_list_schedules_returns_empty_list():
    mock_list = MagicMock(return_value=[])
    with patch(PATCH_LIST, mock_list):
        result = DynamoDBScheduleService().list_schedules('user-99')
    assert result == []


# ---------------------------------------------------------------------------
# create_schedule
# ---------------------------------------------------------------------------

def test_create_schedule_delegates():
    expected = {'id': 'new-sched', 'status': 'ENABLED'}
    mock_create = MagicMock(return_value=expected)
    with patch(PATCH_CREATE, mock_create):
        svc = DynamoDBScheduleService()
        result = svc.create_schedule(
            agent_id='agent-1',
            user_id='user-1',
            agent_user_id='agent-owner',
            cron_expression='0 9 ? * MON *',
            user_message='run now',
        )
    mock_create.assert_called_once_with(
        'agent-1', 'user-1', 'agent-owner', '0 9 ? * MON *', 'run now'
    )
    assert result == expected


def test_create_schedule_passes_all_args():
    mock_create = MagicMock(return_value={})
    with patch(PATCH_CREATE, mock_create):
        DynamoDBScheduleService().create_schedule(
            agent_id='a', user_id='u', agent_user_id='au',
            cron_expression='* * * * ?', user_message='hello',
        )
    args = mock_create.call_args[0]
    assert args == ('a', 'u', 'au', '* * * * ?', 'hello')


# ---------------------------------------------------------------------------
# update_schedule
# ---------------------------------------------------------------------------

def test_update_schedule_delegates():
    expected = {'id': 'sched-1', 'cronExpression': '0 10 ? * TUE *'}
    mock_update = MagicMock(return_value=expected)
    with patch(PATCH_UPDATE, mock_update):
        svc = DynamoDBScheduleService()
        result = svc.update_schedule(
            schedule_id='sched-1',
            user_id='user-1',
            agent_id='agent-1',
            agent_user_id='agent-owner',
            cron_expression='0 10 ? * TUE *',
            user_message='updated message',
        )
    mock_update.assert_called_once_with(
        'sched-1', 'user-1', 'agent-1', 'agent-owner',
        '0 10 ? * TUE *', 'updated message',
    )
    assert result == expected


def test_update_schedule_passes_all_args():
    mock_update = MagicMock(return_value={})
    with patch(PATCH_UPDATE, mock_update):
        DynamoDBScheduleService().update_schedule(
            schedule_id='sid',
            user_id='uid',
            agent_id='aid',
            agent_user_id='auid',
            cron_expression='cron',
            user_message='msg',
        )
    args = mock_update.call_args[0]
    assert args == ('sid', 'uid', 'aid', 'auid', 'cron', 'msg')


# ---------------------------------------------------------------------------
# delete_schedule
# ---------------------------------------------------------------------------

def test_delete_schedule_delegates():
    expected = {'message': 'Schedule sched-99 deleted successfully'}
    mock_delete = MagicMock(return_value=expected)
    with patch(PATCH_DELETE, mock_delete):
        svc = DynamoDBScheduleService()
        result = svc.delete_schedule('sched-99', 'user-1')
    mock_delete.assert_called_once_with('sched-99', 'user-1')
    assert result == expected


def test_delete_schedule_passes_correct_order():
    """Verify schedule_id comes before user_id in the delegated call."""
    mock_delete = MagicMock(return_value={})
    with patch(PATCH_DELETE, mock_delete):
        DynamoDBScheduleService().delete_schedule('schedule-id', 'user-id')
    args = mock_delete.call_args[0]
    assert args[0] == 'schedule-id'
    assert args[1] == 'user-id'


# ---------------------------------------------------------------------------
# Delegation return values are passed through unchanged
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('return_val', [
    None,
    [],
    {'status': 'ok'},
    [{'id': 'x'}, {'id': 'y'}],
])
def test_list_schedules_return_value_passthrough(return_val):
    with patch(PATCH_LIST, MagicMock(return_value=return_val)):
        result = DynamoDBScheduleService().list_schedules('u')
    assert result == return_val


@pytest.mark.parametrize('return_val', [
    None,
    {'id': 'new'},
    {'id': 'updated', 'cronExpression': '* * * * ?'},
    {'message': 'Schedule X deleted successfully'},
])
def test_create_schedule_return_value_passthrough(return_val):
    with patch(PATCH_CREATE, MagicMock(return_value=return_val)):
        result = DynamoDBScheduleService().create_schedule(
            'a', 'u', 'au', 'cron', 'msg'
        )
    assert result == return_val
