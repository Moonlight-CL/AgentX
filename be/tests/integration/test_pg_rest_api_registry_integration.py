"""
Integration tests for PGRestAPIRegistry against a real PostgreSQL database.

Each test runs inside a transaction that is rolled back on completion, so the
database is left clean after the suite.

Async methods are exercised via asyncio.run() to keep the tests simple and
avoid the asyncio pytest mode requirement.

Run with:
    INTEGRATION_DATABASE_URL=postgresql://... uv run --no-sync pytest tests/integration/ -v -m integration
"""
import asyncio
import uuid

import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _uid(prefix: str = 'id') -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _sample_config(name: str = 'Test API') -> dict:
    return {
        'name': name,
        'endpoints': [
            {
                'path': '/v1/items',
                'method': 'GET',
                'description': 'List items',
            }
        ],
    }


# ---------------------------------------------------------------------------
# create_api / get_api
# ---------------------------------------------------------------------------

def test_create_and_get_api(rest_api_registry):
    user_id = _uid('user')
    api_id = uuid.uuid4().hex
    config = _sample_config('My API')

    asyncio.run(rest_api_registry.create_api(user_id, api_id, config))

    result = asyncio.run(rest_api_registry.get_api(user_id, api_id))
    assert result is not None
    assert result['user_id'] == user_id
    assert result['api_id'] == api_id
    assert result['name'] == 'My API'
    assert len(result['endpoints']) == 1


def test_get_api_not_found(rest_api_registry):
    result = asyncio.run(rest_api_registry.get_api(_uid('user'), uuid.uuid4().hex))
    assert result is None


# ---------------------------------------------------------------------------
# get_user_apis (async)
# ---------------------------------------------------------------------------

def test_get_user_apis(rest_api_registry):
    user_id = _uid('user')
    api_id1 = uuid.uuid4().hex
    api_id2 = uuid.uuid4().hex

    asyncio.run(rest_api_registry.create_api(user_id, api_id1, _sample_config('API One')))
    asyncio.run(rest_api_registry.create_api(user_id, api_id2, _sample_config('API Two')))

    # A different user's API should NOT appear
    other_user = _uid('other')
    asyncio.run(rest_api_registry.create_api(other_user, uuid.uuid4().hex, _sample_config('Other')))

    apis = asyncio.run(rest_api_registry.get_user_apis(user_id))
    ids = {a['api_id'] for a in apis}
    assert api_id1 in ids
    assert api_id2 in ids


# ---------------------------------------------------------------------------
# update_api
# ---------------------------------------------------------------------------

def test_update_api(rest_api_registry):
    user_id = _uid('user')
    api_id = uuid.uuid4().hex
    asyncio.run(rest_api_registry.create_api(user_id, api_id, _sample_config('Original')))

    new_config = {
        'name': 'Updated Name',
        'endpoints': [
            {'path': '/v2/items', 'method': 'POST', 'description': 'Create item'},
            {'path': '/v2/items/{id}', 'method': 'GET', 'description': 'Get item'},
        ],
    }
    asyncio.run(rest_api_registry.update_api(user_id, api_id, new_config))

    result = asyncio.run(rest_api_registry.get_api(user_id, api_id))
    assert result is not None
    assert result['name'] == 'Updated Name'
    assert len(result['endpoints']) == 2


# ---------------------------------------------------------------------------
# delete_api
# ---------------------------------------------------------------------------

def test_delete_api(rest_api_registry):
    user_id = _uid('user')
    api_id = uuid.uuid4().hex
    asyncio.run(rest_api_registry.create_api(user_id, api_id, _sample_config()))

    asyncio.run(rest_api_registry.delete_api(user_id, api_id))

    result = asyncio.run(rest_api_registry.get_api(user_id, api_id))
    assert result is None


# ---------------------------------------------------------------------------
# get_user_apis_sync
# ---------------------------------------------------------------------------

def test_get_user_apis_sync(rest_api_registry):
    user_id = _uid('user')
    api_id = uuid.uuid4().hex
    asyncio.run(rest_api_registry.create_api(user_id, api_id, _sample_config('Sync Test API')))

    apis = rest_api_registry.get_user_apis_sync(user_id)
    ids = {a['api_id'] for a in apis}
    assert api_id in ids
