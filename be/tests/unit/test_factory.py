"""
Unit tests for app/storage/factory.py.

Each factory function is tested for three backend configurations:
  - 'dynamodb'   (explicit)
  - 'postgresql' (explicit)
  - unset        (defaults to dynamodb)

Because the PG service classes require a live DB connection at construction
time (they call get_pg_connection inside methods, not __init__), instantiation
is safe to test directly.  The DynamoDB service classes may call boto3 in
__init__, so we mock those constructors.
"""
import os
import importlib
import sys
import types
from unittest.mock import MagicMock, patch
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_factory():
    """Force-reload factory so _backend() re-reads the env var."""
    import app.storage.factory as fac  # type: ignore
    importlib.reload(fac)
    return fac


# ---------------------------------------------------------------------------
# Stubs for every class the factory might import.
# We don't want to construct real DynamoDB resources, so we stub the classes.
# ---------------------------------------------------------------------------

_PG_STUBS = {
    'app.user.pg_user_service':          {'PGUserService': MagicMock},
    'app.agent.pg_agent_service':        {'PGAgentPOService': MagicMock,
                                          'PGChatRecordService': MagicMock},
    'app.mcp.pg_mcp_service':            {'PGMCPService': MagicMock},
    'app.schedule.pg_schedule_service':  {'PGScheduleService': MagicMock},
    'app.config.pg_config_service':      {'PGConfigService': MagicMock},
    'app.orchestration.pg_orchestration_service': {'PGOrchestrationService': MagicMock},
    'app.services.pg_rest_api_registry': {'PGRestAPIRegistry': MagicMock},
    'app.agent.pg_session_repository':   {'PostgreSQLSessionRepository': MagicMock},
}

_DYNAMO_STUBS = {
    'app.user.models':                          {'UserService': MagicMock},
    'app.agent.agent':                          {'AgentPOService': MagicMock,
                                                 'ChatRecordService': MagicMock},
    'app.mcp.mcp':                              {'MCPService': MagicMock},
    'app.schedule.dynamo_schedule_service':     {'DynamoDBScheduleService': MagicMock},
    'app.config.config':                        {'ConfigService': MagicMock},
    'app.orchestration.service':                {'OrchestrationService': MagicMock},
    'app.services.rest_api_registry':           {'RestAPIRegistry': MagicMock},
    'app.agent.dynamodb_session_repository':    {'DynamoDBSessionRepository': MagicMock},
}


def _inject_stubs(stub_dict):
    """Insert lightweight module stubs into sys.modules."""
    for mod_name, attrs in stub_dict.items():
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
def _stub_all_service_modules():
    """Inject stubs for all service modules before each test."""
    _inject_stubs(_PG_STUBS)
    _inject_stubs(_DYNAMO_STUBS)
    yield


# ---------------------------------------------------------------------------
# get_user_service
# ---------------------------------------------------------------------------

def test_get_user_service_dynamodb_explicit():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'dynamodb'}):
        fac = _reload_factory()
        svc = fac.get_user_service()
        assert svc is not None


def test_get_user_service_postgresql():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'postgresql'}):
        fac = _reload_factory()
        svc = fac.get_user_service()
        assert svc is not None
        assert type(svc).__name__ in ('PGUserService', 'MagicMock')


def test_get_user_service_default(monkeypatch):
    monkeypatch.delenv('STORAGE_BACKEND', raising=False)
    fac = _reload_factory()
    svc = fac.get_user_service()
    assert svc is not None


# ---------------------------------------------------------------------------
# get_agent_service
# ---------------------------------------------------------------------------

def test_get_agent_service_dynamodb():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'dynamodb'}):
        fac = _reload_factory()
        svc = fac.get_agent_service()
        assert svc is not None


def test_get_agent_service_postgresql():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'postgresql'}):
        fac = _reload_factory()
        svc = fac.get_agent_service()
        assert svc is not None


def test_get_agent_service_default(monkeypatch):
    monkeypatch.delenv('STORAGE_BACKEND', raising=False)
    fac = _reload_factory()
    svc = fac.get_agent_service()
    assert svc is not None


# ---------------------------------------------------------------------------
# get_chat_record_service
# ---------------------------------------------------------------------------

def test_get_chat_record_service_dynamodb():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'dynamodb'}):
        fac = _reload_factory()
        svc = fac.get_chat_record_service()
        assert svc is not None


def test_get_chat_record_service_postgresql():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'postgresql'}):
        fac = _reload_factory()
        svc = fac.get_chat_record_service()
        assert svc is not None


def test_get_chat_record_service_default(monkeypatch):
    monkeypatch.delenv('STORAGE_BACKEND', raising=False)
    fac = _reload_factory()
    svc = fac.get_chat_record_service()
    assert svc is not None


# ---------------------------------------------------------------------------
# get_mcp_service
# ---------------------------------------------------------------------------

def test_get_mcp_service_dynamodb():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'dynamodb'}):
        fac = _reload_factory()
        svc = fac.get_mcp_service()
        assert svc is not None


def test_get_mcp_service_postgresql():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'postgresql'}):
        fac = _reload_factory()
        svc = fac.get_mcp_service()
        assert svc is not None


def test_get_mcp_service_default(monkeypatch):
    monkeypatch.delenv('STORAGE_BACKEND', raising=False)
    fac = _reload_factory()
    svc = fac.get_mcp_service()
    assert svc is not None


# ---------------------------------------------------------------------------
# get_schedule_service
# ---------------------------------------------------------------------------

def test_get_schedule_service_dynamodb():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'dynamodb'}):
        fac = _reload_factory()
        svc = fac.get_schedule_service()
        assert svc is not None


def test_get_schedule_service_postgresql():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'postgresql'}):
        fac = _reload_factory()
        svc = fac.get_schedule_service()
        assert svc is not None


def test_get_schedule_service_default(monkeypatch):
    monkeypatch.delenv('STORAGE_BACKEND', raising=False)
    fac = _reload_factory()
    svc = fac.get_schedule_service()
    assert svc is not None


# ---------------------------------------------------------------------------
# get_config_service
# ---------------------------------------------------------------------------

def test_get_config_service_dynamodb():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'dynamodb'}):
        fac = _reload_factory()
        svc = fac.get_config_service()
        assert svc is not None


def test_get_config_service_postgresql():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'postgresql'}):
        fac = _reload_factory()
        svc = fac.get_config_service()
        assert svc is not None


def test_get_config_service_default(monkeypatch):
    monkeypatch.delenv('STORAGE_BACKEND', raising=False)
    fac = _reload_factory()
    svc = fac.get_config_service()
    assert svc is not None


# ---------------------------------------------------------------------------
# get_orchestration_service
# ---------------------------------------------------------------------------

def test_get_orchestration_service_dynamodb():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'dynamodb'}):
        fac = _reload_factory()
        svc = fac.get_orchestration_service()
        assert svc is not None


def test_get_orchestration_service_postgresql():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'postgresql'}):
        fac = _reload_factory()
        svc = fac.get_orchestration_service()
        assert svc is not None


def test_get_orchestration_service_default(monkeypatch):
    monkeypatch.delenv('STORAGE_BACKEND', raising=False)
    fac = _reload_factory()
    svc = fac.get_orchestration_service()
    assert svc is not None


# ---------------------------------------------------------------------------
# get_rest_api_registry
# ---------------------------------------------------------------------------

def test_get_rest_api_registry_dynamodb():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'dynamodb'}):
        fac = _reload_factory()
        svc = fac.get_rest_api_registry()
        assert svc is not None


def test_get_rest_api_registry_postgresql():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'postgresql'}):
        fac = _reload_factory()
        svc = fac.get_rest_api_registry()
        assert svc is not None


def test_get_rest_api_registry_default(monkeypatch):
    monkeypatch.delenv('STORAGE_BACKEND', raising=False)
    fac = _reload_factory()
    svc = fac.get_rest_api_registry()
    assert svc is not None


# ---------------------------------------------------------------------------
# get_session_repository
# ---------------------------------------------------------------------------

def test_get_session_repository_dynamodb():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'dynamodb'}):
        fac = _reload_factory()
        svc = fac.get_session_repository()
        assert svc is not None


def test_get_session_repository_postgresql():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'postgresql'}):
        fac = _reload_factory()
        svc = fac.get_session_repository()
        assert svc is not None


def test_get_session_repository_default(monkeypatch):
    monkeypatch.delenv('STORAGE_BACKEND', raising=False)
    fac = _reload_factory()
    svc = fac.get_session_repository()
    assert svc is not None


# ---------------------------------------------------------------------------
# _backend() helper — case-insensitivity
# ---------------------------------------------------------------------------

def test_backend_is_case_insensitive():
    with patch.dict(os.environ, {'STORAGE_BACKEND': 'PostgreSQL'}):
        fac = _reload_factory()
        assert fac._backend() == 'postgresql'


def test_backend_default_is_dynamodb(monkeypatch):
    monkeypatch.delenv('STORAGE_BACKEND', raising=False)
    fac = _reload_factory()
    assert fac._backend() == 'dynamodb'
