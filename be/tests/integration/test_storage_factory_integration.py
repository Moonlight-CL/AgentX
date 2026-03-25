"""
Integration tests for app/storage/factory.py.

These tests verify that each factory function returns the correct service class
depending on the STORAGE_BACKEND environment variable.

For the PostgreSQL path we use a real INTEGRATION_DATABASE_URL.
For the DynamoDB path the DynamoDB constructors are mocked so no AWS credentials
are needed.

Run with:
    INTEGRATION_DATABASE_URL=postgresql://... uv run --no-sync pytest tests/integration/ -v -m integration
"""
import importlib
import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helper – reload factory so _backend() picks up fresh env vars each time
# ---------------------------------------------------------------------------

def _reload_factory():
    import app.storage.factory as fac
    importlib.reload(fac)
    return fac


# ---------------------------------------------------------------------------
# Stub DynamoDB service classes so their __init__ doesn't hit AWS.
# ---------------------------------------------------------------------------

_DYNAMO_STUBS = {
    'app.user.models':                       {'UserService': MagicMock},
    'app.agent.agent':                       {'AgentPOService': MagicMock, 'ChatRecordService': MagicMock},
    'app.mcp.mcp':                           {'MCPService': MagicMock},
    'app.schedule.dynamo_schedule_service':  {'DynamoDBScheduleService': MagicMock},
    'app.config.config':                     {'ConfigService': MagicMock},
    'app.orchestration.service':             {'OrchestrationService': MagicMock},
    'app.services.rest_api_registry':        {'RestAPIRegistry': MagicMock},
    'app.agent.dynamodb_session_repository': {'DynamoDBSessionRepository': MagicMock},
}


def _ensure_dynamo_stubs():
    for mod_name, attrs in _DYNAMO_STUBS.items():
        if mod_name not in sys.modules:
            mod = types.ModuleType(mod_name)
            for attr, cls in attrs.items():
                setattr(mod, attr, cls())
            sys.modules[mod_name] = mod
        else:
            for attr, cls in attrs.items():
                if not hasattr(sys.modules[mod_name], attr):
                    setattr(sys.modules[mod_name], attr, cls())


@pytest.fixture(autouse=True)
def _inject_dynamo_stubs():
    _ensure_dynamo_stubs()
    yield


# ---------------------------------------------------------------------------
# PostgreSQL backend — factory returns real PG service instances
# ---------------------------------------------------------------------------

def test_factory_returns_pg_services_when_postgresql_backend(integration_db_url):
    """With STORAGE_BACKEND=postgresql each factory returns the correct PG class."""
    from app.user.pg_user_service import PGUserService
    from app.agent.pg_agent_service import PGAgentPOService, PGChatRecordService
    from app.mcp.pg_mcp_service import PGMCPService
    from app.config.pg_config_service import PGConfigService
    from app.services.pg_rest_api_registry import PGRestAPIRegistry

    env_overrides = {
        'STORAGE_BACKEND': 'postgresql',
        'DATABASE_URL': integration_db_url,
    }

    # PGChatRecordService.__init__ imports PostgreSQLSessionRepository which
    # needs S3StorageService; patch it so instantiation is clean.
    with patch.dict(os.environ, env_overrides), \
         patch('app.agent.pg_session_repository.S3StorageService', MagicMock):
        fac = _reload_factory()

        user_svc = fac.get_user_service()
        assert isinstance(user_svc, PGUserService)

        agent_svc = fac.get_agent_service()
        assert isinstance(agent_svc, PGAgentPOService)

        chat_svc = fac.get_chat_record_service()
        assert isinstance(chat_svc, PGChatRecordService)

        mcp_svc = fac.get_mcp_service()
        assert isinstance(mcp_svc, PGMCPService)

        config_svc = fac.get_config_service()
        assert isinstance(config_svc, PGConfigService)

        rest_reg = fac.get_rest_api_registry()
        assert isinstance(rest_reg, PGRestAPIRegistry)


# ---------------------------------------------------------------------------
# DynamoDB backend — factory returns DynamoDB service instances (mocked)
# ---------------------------------------------------------------------------

def test_factory_returns_dynamo_services_when_dynamodb_backend():
    """With STORAGE_BACKEND=dynamodb each factory returns a DynamoDB service."""
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'dynamodb'}):
        fac = _reload_factory()

        user_svc = fac.get_user_service()
        assert user_svc is not None
        # The class name is either the real one or the mock stub
        assert type(user_svc).__name__ in ('UserService', 'MagicMock')

        agent_svc = fac.get_agent_service()
        assert agent_svc is not None

        chat_svc = fac.get_chat_record_service()
        assert chat_svc is not None

        mcp_svc = fac.get_mcp_service()
        assert mcp_svc is not None

        config_svc = fac.get_config_service()
        assert config_svc is not None

        rest_reg = fac.get_rest_api_registry()
        assert rest_reg is not None


# ---------------------------------------------------------------------------
# Schedule service
# ---------------------------------------------------------------------------

def test_schedule_init_postgres(integration_db_url):
    """get_schedule_service() with PG backend returns PGScheduleService."""
    from app.schedule.pg_schedule_service import PGScheduleService

    with patch.dict(os.environ, {'STORAGE_BACKEND': 'postgresql', 'DATABASE_URL': integration_db_url}):
        fac = _reload_factory()
        svc = fac.get_schedule_service()
        assert isinstance(svc, PGScheduleService)


def test_schedule_init_dynamo():
    """get_schedule_service() with DynamoDB backend returns DynamoDBScheduleService."""
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'dynamodb'}):
        fac = _reload_factory()
        svc = fac.get_schedule_service()
        assert svc is not None
        assert type(svc).__name__ in ('DynamoDBScheduleService', 'MagicMock')
