"""
Integration tests for PGMCPService against a real PostgreSQL database.

Each test runs inside a transaction that is rolled back on completion, so the
database is left clean after the suite.

Run with:
    INTEGRATION_DATABASE_URL=postgresql://... uv run --no-sync pytest tests/integration/ -v -m integration
"""
import uuid

import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _uid(prefix: str = 'id') -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _make_server(**overrides):
    """Return an HttpMCPServer with sensible defaults."""
    from app.mcp.mcp import HttpMCPServer

    defaults = dict(
        id=uuid.uuid4().hex,
        name='Test MCP Server',
        desc='Integration test server',
        host='https://mcp.example.com/sse',
    )
    defaults.update(overrides)
    return HttpMCPServer(**defaults)


# ---------------------------------------------------------------------------
# add_mcp_server / get_mcp_server
# ---------------------------------------------------------------------------

def test_add_and_get_mcp_server(mcp_service):
    user_id = _uid('user')
    server = _make_server()
    mcp_service.add_mcp_server(server, user_id=user_id)

    fetched = mcp_service.get_mcp_server(user_id, server.id)
    assert fetched is not None
    assert fetched.id == server.id
    assert fetched.name == server.name
    assert fetched.host == server.host


def test_add_mcp_server_with_headers(mcp_service):
    user_id = _uid('user')
    headers = {'Authorization': 'Bearer token123', 'X-Custom': 'value'}
    server = _make_server(headers=headers)
    mcp_service.add_mcp_server(server, user_id=user_id)

    fetched = mcp_service.get_mcp_server(user_id, server.id)
    assert fetched is not None
    assert fetched.headers == headers


def test_get_mcp_server_not_found(mcp_service):
    result = mcp_service.get_mcp_server(_uid('user'), uuid.uuid4().hex)
    assert result is None


# ---------------------------------------------------------------------------
# list_mcp_servers
# ---------------------------------------------------------------------------

def test_list_mcp_servers_user_and_public(mcp_service):
    user_id = _uid('user')
    user_server = _make_server(name='User Server')
    public_server = _make_server(name='Public Server')

    mcp_service.add_mcp_server(user_server, user_id=user_id)
    mcp_service.add_mcp_server(public_server, user_id='public')

    servers = mcp_service.list_mcp_servers(user_id)
    ids = {s.id for s in servers}
    assert user_server.id in ids
    assert public_server.id in ids


# ---------------------------------------------------------------------------
# delete_mcp_server
# ---------------------------------------------------------------------------

def test_delete_mcp_server(mcp_service):
    user_id = _uid('user')
    server = _make_server()
    mcp_service.add_mcp_server(server, user_id=user_id)

    result = mcp_service.delete_mcp_server(user_id, server.id)
    assert result is True

    assert mcp_service.get_mcp_server(user_id, server.id) is None


# ---------------------------------------------------------------------------
# add_mcp_server upsert behaviour
# ---------------------------------------------------------------------------

def test_add_mcp_server_upsert(mcp_service):
    """Calling add_mcp_server twice with the same (user_id, id) updates the record."""
    user_id = _uid('user')
    server_id = uuid.uuid4().hex

    first = _make_server(id=server_id, name='First Name', host='https://first.example.com/sse')
    mcp_service.add_mcp_server(first, user_id=user_id)

    second = _make_server(id=server_id, name='Updated Name', host='https://updated.example.com/sse')
    mcp_service.add_mcp_server(second, user_id=user_id)

    servers = mcp_service.list_mcp_servers(user_id)
    matching = [s for s in servers if s.id == server_id]
    assert len(matching) == 1
    assert matching[0].name == 'Updated Name'
    assert matching[0].host == 'https://updated.example.com/sse'
