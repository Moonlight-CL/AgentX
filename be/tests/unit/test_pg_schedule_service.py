"""
Unit tests for app/schedule/pg_schedule_service.py — PGScheduleService.

All tests patch 'app.schedule.pg_schedule_service.get_pg_connection' and
'app.schedule.pg_schedule_service._get_eventbridge' so that no real AWS
or database connections are required.
"""
import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from app.schedule.pg_schedule_service import PGScheduleService  # type: ignore
from fastapi import HTTPException  # type: ignore  (stubbed in conftest)

# ---------------------------------------------------------------------------
# Column layout for agent_schedules table
# ---------------------------------------------------------------------------

SCHEDULE_COLUMNS = [
    'user_id', 'id', 'agent_id', 'agent_user_id', 'agent_name',
    'cron_expression', 'status', 'eventbridge_schedule_name',
    'created_at', 'updated_at', 'user_message',
]

SCHEDULE_DESCRIPTION = [(col,) for col in SCHEDULE_COLUMNS]


def _schedule_row(**overrides):
    defaults = {
        'user_id': 'u1', 'id': 'sched-1', 'agent_id': 'a1',
        'agent_user_id': 'u1', 'agent_name': 'Test Agent',
        'cron_expression': '0 9 * * ?',
        'status': 'ENABLED',
        'eventbridge_schedule_name': 'agent-schedule-sched-1',
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-01T00:00:00Z',
        'user_message': 'run daily',
    }
    defaults.update(overrides)
    return defaults


def _schedule_tuple(d):
    return tuple(d[c] for c in SCHEDULE_COLUMNS)


# ---------------------------------------------------------------------------
# Context-manager helpers
# ---------------------------------------------------------------------------

class _FakeCursor:
    def __init__(self, fetchone_val=None, fetchall_val=None):
        self.execute = MagicMock()
        self._fetchone_val = fetchone_val
        self._fetchall_val = fetchall_val or []
        self.description = list(SCHEDULE_DESCRIPTION)

    def fetchone(self):
        return self._fetchone_val

    def fetchall(self):
        return self._fetchall_val

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


class _FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        pass


def _pg(cursor):
    @contextmanager
    def _cm():
        yield _FakeConn(cursor)
    return _cm


PATCH_TARGET = 'app.schedule.pg_schedule_service.get_pg_connection'
EB_PATCH = 'app.schedule.pg_schedule_service._get_eventbridge'


# ===========================================================================
# list_schedules
# ===========================================================================

def test_list_schedules_returns_list():
    rows = [
        _schedule_tuple(_schedule_row(id='s1')),
        _schedule_tuple(_schedule_row(id='s2')),
    ]
    cur = _FakeCursor(fetchall_val=rows)
    with patch(PATCH_TARGET, _pg(cur)):
        svc = PGScheduleService()
        result = svc.list_schedules('u1')
    assert len(result) == 2
    assert {r['id'] for r in result} == {'s1', 's2'}


def test_list_schedules_db_error():
    @contextmanager
    def _boom():
        raise RuntimeError('db error')
        yield  # noqa

    with patch(PATCH_TARGET, _boom):
        svc = PGScheduleService()
        with pytest.raises(HTTPException) as exc_info:
            svc.list_schedules('u1')
    assert exc_info.value.status_code == 500


# ===========================================================================
# _validate_cron_expression
# ===========================================================================

def test_validate_cron_expression_valid():
    svc = PGScheduleService()
    result = svc._validate_cron_expression('0 9 * * ?')
    assert result == 'cron(0 9 * * ? *)'


def test_validate_cron_expression_invalid_parts():
    svc = PGScheduleService()
    with pytest.raises(HTTPException) as exc_info:
        svc._validate_cron_expression('0 9 *')  # only 3 parts
    assert exc_info.value.status_code == 400


def test_validate_cron_expression_both_day_fields_set():
    """Both day-of-month (field 2) and day-of-week (field 4) are non-'?' → error."""
    svc = PGScheduleService()
    with pytest.raises(HTTPException) as exc_info:
        svc._validate_cron_expression('0 9 5 * 1')  # neither is '?'
    assert exc_info.value.status_code == 400


# ===========================================================================
# create_schedule
# ===========================================================================

def test_create_schedule_success():
    mock_eb = MagicMock()
    mock_eb.create_schedule.return_value = {}
    cur = _FakeCursor()

    with patch(EB_PATCH, return_value=mock_eb):
        with patch(PATCH_TARGET, _pg(cur)):
            svc = PGScheduleService()
            with patch.object(svc, '_get_agent_name', return_value='Test Agent'):
                result = svc.create_schedule(
                    agent_id='a1', user_id='u1', agent_user_id='u1',
                    cron_expression='0 9 * * ?', user_message='run daily',
                )

    assert result['agentId'] == 'a1'
    assert result['status'] == 'ENABLED'
    assert 'id' in result
    mock_eb.create_schedule.assert_called_once()
    cur.execute.assert_called_once()


def test_create_schedule_missing_agent_id():
    svc = PGScheduleService()
    with pytest.raises(HTTPException) as exc_info:
        svc.create_schedule(
            agent_id='', user_id='u1', agent_user_id='u1',
            cron_expression='0 9 * * ?', user_message='msg',
        )
    assert exc_info.value.status_code == 400


def test_create_schedule_missing_cron():
    svc = PGScheduleService()
    with pytest.raises(HTTPException) as exc_info:
        svc.create_schedule(
            agent_id='a1', user_id='u1', agent_user_id='u1',
            cron_expression='', user_message='msg',
        )
    assert exc_info.value.status_code == 400


# ===========================================================================
# update_schedule
# ===========================================================================

def test_update_schedule_success():
    row = _schedule_tuple(_schedule_row())
    mock_eb = MagicMock()
    mock_eb.update_schedule.return_value = {}
    update_cur = _FakeCursor()
    call_idx = [0]

    @contextmanager
    def _ctx():
        if call_idx[0] == 0:
            # lookup existing schedule
            cur = _FakeCursor(fetchone_val=row)
        else:
            # UPDATE
            cur = _FakeCursor()
        call_idx[0] += 1
        yield _FakeConn(cur)

    with patch(EB_PATCH, return_value=mock_eb):
        with patch(PATCH_TARGET, _ctx):
            svc = PGScheduleService()
            with patch.object(svc, '_get_agent_name', return_value='Updated Agent'):
                result = svc.update_schedule(
                    schedule_id='sched-1', user_id='u1', agent_id='a1',
                    agent_user_id='u1', cron_expression='0 10 * * ?',
                    user_message='updated msg',
                )

    assert result['id'] == 'sched-1'
    mock_eb.update_schedule.assert_called_once()


def test_update_schedule_not_found():
    cur = _FakeCursor(fetchone_val=None)
    mock_eb = MagicMock()

    with patch(EB_PATCH, return_value=mock_eb):
        with patch(PATCH_TARGET, _pg(cur)):
            svc = PGScheduleService()
            with pytest.raises(HTTPException) as exc_info:
                svc.update_schedule(
                    schedule_id='missing', user_id='u1', agent_id='a1',
                    agent_user_id='u1', cron_expression='0 9 * * ?',
                    user_message='msg',
                )
    assert exc_info.value.status_code == 404


# ===========================================================================
# delete_schedule
# ===========================================================================

def test_delete_schedule_success():
    row = _schedule_tuple(_schedule_row())
    mock_eb = MagicMock()
    mock_eb.delete_schedule.return_value = {}
    call_idx = [0]

    @contextmanager
    def _ctx():
        if call_idx[0] == 0:
            # lookup
            cur = _FakeCursor(fetchone_val=row)
        else:
            # DELETE
            cur = _FakeCursor()
        call_idx[0] += 1
        yield _FakeConn(cur)

    with patch(EB_PATCH, return_value=mock_eb):
        with patch(PATCH_TARGET, _ctx):
            svc = PGScheduleService()
            result = svc.delete_schedule('sched-1', 'u1')

    assert 'deleted' in result['message'].lower()
    mock_eb.delete_schedule.assert_called_once_with(Name='agent-schedule-sched-1')


def test_delete_schedule_not_found():
    cur = _FakeCursor(fetchone_val=None)
    mock_eb = MagicMock()

    with patch(EB_PATCH, return_value=mock_eb):
        with patch(PATCH_TARGET, _pg(cur)):
            svc = PGScheduleService()
            with pytest.raises(HTTPException) as exc_info:
                svc.delete_schedule('missing', 'u1')
    assert exc_info.value.status_code == 404


def test_delete_schedule_without_eventbridge_name():
    """Schedule row without an eventbridge_schedule_name — skip EB call but delete from DB."""
    row = _schedule_tuple(_schedule_row(eventbridge_schedule_name=None))
    mock_eb = MagicMock()
    call_idx = [0]

    @contextmanager
    def _ctx():
        if call_idx[0] == 0:
            # lookup
            cur = _FakeCursor(fetchone_val=row)
        else:
            # DELETE
            cur = _FakeCursor()
        call_idx[0] += 1
        yield _FakeConn(cur)

    with patch(EB_PATCH, return_value=mock_eb):
        with patch(PATCH_TARGET, _ctx):
            svc = PGScheduleService()
            result = svc.delete_schedule('sched-1', 'u1')

    # EventBridge delete should NOT be called when name is None
    mock_eb.delete_schedule.assert_not_called()
    assert 'deleted' in result['message'].lower()
