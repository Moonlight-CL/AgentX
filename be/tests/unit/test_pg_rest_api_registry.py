"""
Unit tests for app/services/pg_rest_api_registry.py — PGRestAPIRegistry.

All tests patch 'app.services.pg_rest_api_registry.get_pg_connection'.

Async methods are tested using asyncio.run() since pytest-asyncio is not
available in this environment.
"""
import json
import asyncio
import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from app.services.pg_rest_api_registry import PGRestAPIRegistry  # type: ignore

# ---------------------------------------------------------------------------
# Column layout
# ---------------------------------------------------------------------------

API_COLUMNS = ['user_id', 'api_id', 'name', 'endpoints', 'created_at', 'updated_at']
API_DESCRIPTION = [(col,) for col in API_COLUMNS]


def _api_row(**overrides):
    defaults = {
        'user_id': 'u1',
        'api_id': 'api-1',
        'name': 'My API',
        'endpoints': '[]',
        'created_at': '2024-01-01T00:00:00',
        'updated_at': '2024-01-01T00:00:00',
    }
    defaults.update(overrides)
    return defaults


def _api_tuple(d):
    return tuple(d[c] for c in API_COLUMNS)


# ---------------------------------------------------------------------------
# Context-manager helpers
# ---------------------------------------------------------------------------

class _FakeCursor:
    def __init__(self, fetchone_val=None, fetchall_val=None):
        self.execute = MagicMock()
        self._fetchone_val = fetchone_val
        self._fetchall_val = fetchall_val or []
        self.description = list(API_DESCRIPTION)

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


PATCH_TARGET = 'app.services.pg_rest_api_registry.get_pg_connection'


# ===========================================================================
# get_user_apis_sync
# ===========================================================================

def test_get_user_apis_sync_returns_list():
    rows = [
        _api_tuple(_api_row(api_id='api-1')),
        _api_tuple(_api_row(api_id='api-2')),
    ]
    cur = _FakeCursor(fetchall_val=rows)
    with patch(PATCH_TARGET, _pg(cur)):
        result = PGRestAPIRegistry().get_user_apis_sync('u1')
    assert len(result) == 2
    assert {r['api_id'] for r in result} == {'api-1', 'api-2'}


def test_get_user_apis_sync_empty():
    cur = _FakeCursor(fetchall_val=[])
    with patch(PATCH_TARGET, _pg(cur)):
        result = PGRestAPIRegistry().get_user_apis_sync('u1')
    assert result == []


def test_get_user_apis_sync_parses_endpoints_json():
    endpoints = [{'path': '/hello', 'method': 'GET'}]
    row = _api_tuple(_api_row(endpoints=json.dumps(endpoints)))
    cur = _FakeCursor(fetchall_val=[row])
    with patch(PATCH_TARGET, _pg(cur)):
        result = PGRestAPIRegistry().get_user_apis_sync('u1')
    assert result[0]['endpoints'] == endpoints


# ===========================================================================
# get_user_apis (async wrapper)
# ===========================================================================

def test_get_user_apis_is_async_wrapper():
    rows = [_api_tuple(_api_row())]
    cur = _FakeCursor(fetchall_val=rows)
    with patch(PATCH_TARGET, _pg(cur)):
        result = asyncio.run(PGRestAPIRegistry().get_user_apis('u1'))
    assert len(result) == 1
    assert result[0]['api_id'] == 'api-1'


# ===========================================================================
# get_api
# ===========================================================================

def test_get_api_found():
    row = _api_tuple(_api_row())
    cur = _FakeCursor(fetchone_val=row)
    with patch(PATCH_TARGET, _pg(cur)):
        result = asyncio.run(PGRestAPIRegistry().get_api('u1', 'api-1'))
    assert result is not None
    assert result['api_id'] == 'api-1'
    assert result['name'] == 'My API'


def test_get_api_not_found():
    cur = _FakeCursor(fetchone_val=None)
    with patch(PATCH_TARGET, _pg(cur)):
        result = asyncio.run(PGRestAPIRegistry().get_api('u1', 'missing'))
    assert result is None


# ===========================================================================
# create_api
# ===========================================================================

def test_create_api_executes_upsert():
    cur = _FakeCursor()
    config = {'name': 'Test API', 'endpoints': [{'path': '/test'}]}
    with patch(PATCH_TARGET, _pg(cur)):
        asyncio.run(PGRestAPIRegistry().create_api('u1', 'api-1', config))
    cur.execute.assert_called_once()
    sql = cur.execute.call_args[0][0]
    assert 'rest_api_registry' in sql.lower()
    assert 'INSERT' in sql.upper()


def test_create_api_returns_dict_with_config():
    cur = _FakeCursor()
    config = {'name': 'Test API', 'endpoints': [{'path': '/test'}]}
    with patch(PATCH_TARGET, _pg(cur)):
        result = asyncio.run(PGRestAPIRegistry().create_api('u1', 'api-1', config))
    assert result['user_id'] == 'u1'
    assert result['api_id'] == 'api-1'
    assert result['name'] == 'Test API'
    assert result['endpoints'] == [{'path': '/test'}]


# ===========================================================================
# update_api
# ===========================================================================

def test_update_api_delegates_to_create_api():
    cur = _FakeCursor()
    config = {'name': 'Updated', 'endpoints': []}
    with patch(PATCH_TARGET, _pg(cur)):
        result = asyncio.run(PGRestAPIRegistry().update_api('u1', 'api-1', config))
    # Should produce same result as create_api
    assert result['user_id'] == 'u1'
    assert result['name'] == 'Updated'
    cur.execute.assert_called_once()


# ===========================================================================
# delete_api
# ===========================================================================

def test_delete_api_executes_delete():
    cur = _FakeCursor()
    with patch(PATCH_TARGET, _pg(cur)):
        asyncio.run(PGRestAPIRegistry().delete_api('u1', 'api-1'))
    cur.execute.assert_called_once()
    sql = cur.execute.call_args[0][0]
    assert 'DELETE' in sql.upper()
    assert 'rest_api_registry' in sql.lower()


# ===========================================================================
# _row_to_dict
# ===========================================================================

def test_row_to_dict_with_json_string_endpoints():
    svc = PGRestAPIRegistry()
    endpoints = [{'path': '/ep', 'method': 'POST'}]
    item = {'user_id': 'u1', 'api_id': 'api-1', 'name': 'Test',
            'endpoints': json.dumps(endpoints), 'created_at': None, 'updated_at': None}
    result = svc._row_to_dict(item)
    assert result['endpoints'] == endpoints


def test_row_to_dict_with_list_endpoints():
    svc = PGRestAPIRegistry()
    endpoints = [{'path': '/ep'}]
    item = {'user_id': 'u1', 'api_id': 'api-1', 'name': 'Test',
            'endpoints': endpoints, 'created_at': None, 'updated_at': None}
    result = svc._row_to_dict(item)
    assert result['endpoints'] == endpoints


def test_row_to_dict_with_no_endpoints():
    svc = PGRestAPIRegistry()
    item = {'user_id': 'u1', 'api_id': 'api-1', 'name': 'Test',
            'endpoints': None, 'created_at': None, 'updated_at': None}
    result = svc._row_to_dict(item)
    assert result['endpoints'] == []
