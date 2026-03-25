"""
Unit tests for app/mcp/pg_mcp_service.py — PGMCPService.

All tests patch 'app.mcp.pg_mcp_service.get_pg_connection' so that no real
database is required.

The PG queries in PGMCPService use:

    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(...)
            rows = cur.fetchall() / cur.fetchone()
            col_names = [desc[0] for desc in cur.description]

The FakeCursor below supports both the context-manager protocol *and* the
description / fetchone / fetchall attributes.
"""
import json
import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock

from app.mcp.pg_mcp_service import PGMCPService  # type: ignore
from app.mcp.mcp import HttpMCPServer  # type: ignore


# ---------------------------------------------------------------------------
# Column layout for http_mcp_servers (must match SELECT * order)
# ---------------------------------------------------------------------------

MCP_COLUMNS = [
    'user_id', 'id', 'name', 'desc', 'host', 'headers',
    'client_id', 'client_secret', 'token_url', 'scope',
]

MCP_DESCRIPTION = [(col,) for col in MCP_COLUMNS]


def _mcp_row(**overrides):
    """Return a tuple row in MCP_COLUMNS order with sensible defaults."""
    defaults = {
        'user_id': 'u1',
        'id': 'srv1',
        'name': 'My MCP',
        'desc': 'A test MCP server',
        'host': 'https://mcp.example.com',
        'headers': None,
        'client_id': None,
        'client_secret': None,
        'token_url': None,
        'scope': None,
    }
    defaults.update(overrides)
    return tuple(defaults[c] for c in MCP_COLUMNS)


def _mcp_dict(**overrides):
    """Return a dict row (as produced by dict(zip(col_names, row)))."""
    defaults = {
        'user_id': 'u1',
        'id': 'srv1',
        'name': 'My MCP',
        'desc': 'A test MCP server',
        'host': 'https://mcp.example.com',
        'headers': None,
        'client_id': None,
        'client_secret': None,
        'token_url': None,
        'scope': None,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Fake cursor / connection helpers
# ---------------------------------------------------------------------------

class _FakeCursor:
    """Cursor supporting context manager and description + fetch* methods."""

    def __init__(self, fetchone_val=None, fetchall_val=None):
        self.execute = MagicMock()
        self._fetchone_val = fetchone_val
        self._fetchall_val = fetchall_val or []
        self.description = list(MCP_DESCRIPTION)

    def fetchone(self):
        return self._fetchone_val

    def fetchall(self):
        return self._fetchall_val

    def __enter__(self):
        return self

    def __exit__(self, *args):
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


def _pg_ctx(cursor):
    @contextmanager
    def _cm():
        yield _FakeConn(cursor)
    return _cm


PATCH_TARGET = 'app.mcp.pg_mcp_service.get_pg_connection'


# ---------------------------------------------------------------------------
# _row_to_server
# ---------------------------------------------------------------------------

def test_row_to_server_basic():
    svc = PGMCPService()
    item = _mcp_dict()
    server = svc._row_to_server(item)
    assert server.id == 'srv1'
    assert server.name == 'My MCP'
    assert server.host == 'https://mcp.example.com'
    assert server.headers is None


def test_row_to_server_with_json_headers():
    svc = PGMCPService()
    item = _mcp_dict(headers='{"Authorization": "Bearer tok"}')
    server = svc._row_to_server(item)
    assert server.headers == {'Authorization': 'Bearer tok'}


def test_row_to_server_with_dict_headers():
    """If psycopg2 already decoded the JSONB column, pass through as-is."""
    svc = PGMCPService()
    item = _mcp_dict(headers={'X-Key': 'val'})
    server = svc._row_to_server(item)
    assert server.headers == {'X-Key': 'val'}


def test_row_to_server_with_oauth_fields():
    svc = PGMCPService()
    item = _mcp_dict(
        client_id='cid',
        client_secret='csec',
        token_url='https://auth.example.com/token',
        scope='read write',
    )
    server = svc._row_to_server(item)
    assert server.client_id == 'cid'
    assert server.token_url == 'https://auth.example.com/token'
    assert server.scope == 'read write'


# ---------------------------------------------------------------------------
# add_mcp_server
# ---------------------------------------------------------------------------

def test_add_mcp_server_new_id():
    """If server.id is None, a UUID is auto-assigned."""
    cur = _FakeCursor()
    server = HttpMCPServer(id=None, name='srv', desc='d', host='http://h')
    with patch_pg(cur):
        PGMCPService().add_mcp_server(server, user_id='u1')
    assert server.id is not None and len(server.id) == 32


def test_add_mcp_server_with_id():
    cur = _FakeCursor()
    server = HttpMCPServer(id='fixed-id', name='srv', desc='d', host='http://h')
    with patch_pg(cur):
        PGMCPService().add_mcp_server(server, user_id='u1')
    assert server.id == 'fixed-id'
    cur.execute.assert_called_once()
    sql, params = cur.execute.call_args[0]
    assert 'INSERT INTO http_mcp_servers' in sql
    assert params[0] == 'u1'
    assert params[1] == 'fixed-id'


def test_add_mcp_server_with_headers():
    cur = _FakeCursor()
    server = HttpMCPServer(
        id='s1', name='srv', desc='d', host='http://h',
        headers={'Authorization': 'Bearer tok'},
    )
    with patch_pg(cur):
        PGMCPService().add_mcp_server(server, user_id='u1')
    _, params = cur.execute.call_args[0]
    headers_json = params[5]
    assert json.loads(headers_json) == {'Authorization': 'Bearer tok'}


def test_add_mcp_server_with_oauth():
    cur = _FakeCursor()
    server = HttpMCPServer(
        id='s1', name='srv', desc='d', host='http://h',
        client_id='cid', client_secret='csec',
        token_url='https://auth/token', scope='read',
    )
    with patch_pg(cur):
        PGMCPService().add_mcp_server(server, user_id='u1')
    _, params = cur.execute.call_args[0]
    assert params[6] == 'cid'
    assert params[7] == 'csec'
    assert params[8] == 'https://auth/token'
    assert params[9] == 'read'


def test_add_mcp_server_default_user_id():
    """Default user_id should be 'public'."""
    cur = _FakeCursor()
    server = HttpMCPServer(id='s1', name='srv', desc='d', host='http://h')
    with patch_pg(cur):
        PGMCPService().add_mcp_server(server)
    _, params = cur.execute.call_args[0]
    assert params[0] == 'public'


# ---------------------------------------------------------------------------
# list_mcp_servers
# ---------------------------------------------------------------------------

def test_list_mcp_servers_returns_both_user_and_public():
    """list_mcp_servers queries user_id then 'public'; results are merged.

    The implementation uses a single cursor inside one with-block and calls
    execute() + fetchall() twice (once per key).  We use a cursor whose
    fetchall() returns successive results based on how many times execute()
    has been called.
    """
    user_row = _mcp_row(user_id='u1', id='s1', name='user-server')
    public_row = _mcp_row(user_id='public', id='s2', name='public-server')

    fetchall_results = [[user_row], [public_row]]

    # Build a cursor that does NOT use MagicMock for execute, so the instance
    # method we define is actually called (MagicMock set in __init__ would
    # shadow a subclass method via instance-attribute precedence).
    class _SeqCursor(_FakeCursor):
        def __init__(self):
            # Call the parent but immediately replace the MagicMock execute
            # with a real counter method so our override is active.
            super().__init__()
            self._exec_count = 0
            # Replace the instance-attribute MagicMock with a bound method
            self.execute = self._execute_impl

        def _execute_impl(self, *args, **kwargs):
            self._exec_count += 1

        def fetchall(self):
            idx = max(self._exec_count - 1, 0)
            idx = min(idx, len(fetchall_results) - 1)
            return fetchall_results[idx]

    cur = _SeqCursor()
    with patch_pg(cur):
        servers = PGMCPService().list_mcp_servers('u1')
    assert len(servers) == 2
    names = {s.name for s in servers}
    assert names == {'user-server', 'public-server'}


def test_list_mcp_servers_empty():
    cur = _FakeCursor(fetchall_val=[])
    with patch_pg(cur):
        servers = PGMCPService().list_mcp_servers('u1')
    assert servers == []


# ---------------------------------------------------------------------------
# get_mcp_server
# ---------------------------------------------------------------------------

def test_get_mcp_server_found_in_user_space():
    """First key is the user_id and the server is found there."""

    class _SeqCursor(_FakeCursor):
        def __init__(self):
            super().__init__()
            self._calls = 0

        def fetchone(self):
            self._calls += 1
            if self._calls == 1:
                return _mcp_row()
            return None

    cur = _SeqCursor()
    with patch_pg(cur):
        server = PGMCPService().get_mcp_server('u1', 'srv1')
    assert server is not None
    assert server.id == 'srv1'


def test_get_mcp_server_found_in_public():
    """Server not in user space but found in public."""

    class _SeqCursor(_FakeCursor):
        def __init__(self):
            super().__init__()
            self._calls = 0

        def fetchone(self):
            self._calls += 1
            if self._calls == 1:
                return None  # not in user space
            return _mcp_row(user_id='public')

    cur = _SeqCursor()
    with patch_pg(cur):
        server = PGMCPService().get_mcp_server('u1', 'srv1')
    assert server is not None


def test_get_mcp_server_not_found():
    cur = _FakeCursor(fetchone_val=None)
    with patch_pg(cur):
        server = PGMCPService().get_mcp_server('u1', 'nonexistent')
    assert server is None


# ---------------------------------------------------------------------------
# delete_mcp_server
# ---------------------------------------------------------------------------

def test_delete_mcp_server_success():
    cur = _FakeCursor()
    with patch_pg(cur):
        result = PGMCPService().delete_mcp_server('u1', 'srv1')
    assert result is True
    cur.execute.assert_called_once()


def test_delete_mcp_server_error():
    @contextmanager
    def _boom():
        raise RuntimeError('db error')
        yield  # pragma: no cover

    with _patch_pg_target(_boom):
        result = PGMCPService().delete_mcp_server('u1', 'srv1')
    assert result is False


# ---------------------------------------------------------------------------
# Patch helpers (defined after tests to allow forward references)
# ---------------------------------------------------------------------------

from unittest.mock import patch  # noqa: E402  (late import is intentional)


def patch_pg(cursor):
    """Context manager: patch get_pg_connection to use *cursor*."""
    return patch(PATCH_TARGET, _pg_ctx(cursor))


def _patch_pg_target(ctx_fn):
    """Patch get_pg_connection with an arbitrary context-manager factory."""
    return patch(PATCH_TARGET, ctx_fn)
