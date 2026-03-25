"""
Integration test conftest for the AgentX backend PostgreSQL storage layer.

Fixtures provided:
  - integration_db_url  (session) : INTEGRATION_DATABASE_URL env var or skip
  - create_schema       (session, autouse) : create all tables from schema.sql
  - db_conn             (function) : psycopg2 connection, autocommit=False, rolled back after test
  - pg_ctx              (function) : drop-in replacement for get_pg_connection that uses db_conn
  - user_service        (function) : PGUserService bound to the test transaction
  - agent_service       (function) : PGAgentPOService bound to the test transaction
  - chat_service        (function) : PGChatRecordService bound to the test transaction
  - mcp_service         (function) : PGMCPService bound to the test transaction
  - config_service      (function) : PGConfigService bound to the test transaction
  - rest_api_registry   (function) : PGRestAPIRegistry bound to the test transaction
"""
import os
import sys
import types
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure be/ directory is on sys.path so 'import app.xxx' works
# ---------------------------------------------------------------------------
_BE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _BE_DIR not in sys.path:
    sys.path.insert(0, _BE_DIR)

# ---------------------------------------------------------------------------
# Restore real psycopg2 in case the unit test conftest replaced it with a stub.
# This must happen before any integration fixture imports psycopg2.
# ---------------------------------------------------------------------------
if 'psycopg2' in sys.modules and not hasattr(sys.modules['psycopg2'], 'connect'):
    for _k in [k for k in list(sys.modules) if k.startswith('psycopg2')]:
        del sys.modules[_k]
import psycopg2 as _psycopg2_real  # noqa: F401 — ensure real module is loaded
import psycopg2.pool as _psycopg2_pool_real
import psycopg2.extras as _psycopg2_extras_real
sys.modules['psycopg2'] = _psycopg2_real
sys.modules['psycopg2.pool'] = _psycopg2_pool_real
sys.modules['psycopg2.extras'] = _psycopg2_extras_real


# ---------------------------------------------------------------------------
# Stub heavy third-party modules that are not needed for PG integration tests.
# These must be registered BEFORE any app module is imported.
# ---------------------------------------------------------------------------

def _make_stub(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__spec__ = None
    return mod


# ---- boto3 / AWS ------------------------------------------------------------
for _mod_name in [
    'boto3',
    'boto3.dynamodb',
    'boto3.dynamodb.conditions',
    'botocore',
    'botocore.config',
    'botocore.exceptions',
]:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _make_stub(_mod_name)

_botocore = sys.modules['botocore']
if not hasattr(_botocore, '__path__'):
    _botocore.__path__ = []

_botocore_exc = sys.modules['botocore.exceptions']
if not hasattr(_botocore_exc, 'ClientError'):
    _botocore_exc.ClientError = type('ClientError', (Exception,), {})

_conditions = sys.modules['boto3.dynamodb.conditions']
_conditions.Key = MagicMock()
_conditions.Attr = MagicMock()

_boto3 = sys.modules['boto3']
_boto3.resource = MagicMock(return_value=MagicMock())
_boto3.client = MagicMock(return_value=MagicMock())
_boto3.dynamodb = sys.modules['boto3.dynamodb']

# ---- strands ----------------------------------------------------------------
for _mod_name in [
    'strands',
    'strands.models',
    'strands.models.bedrock',
    'strands.tools',
    'strands.tools.mcp',
    'strands.tools.mcp.mcp_client',
    'strands.session',
    'strands.session.repository_session_manager',
    'strands.session.session_repository',
    'strands.types',
    'strands.types.session',
    'strands.types.content',
    'mcp',
    'mcp.client',
    'mcp.client.streamable_http',
    'httpx',
    'fastapi',
    'fastapi.exceptions',
]:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _make_stub(_mod_name)

_strands_session_pkg = sys.modules['strands.session']
if not hasattr(_strands_session_pkg, '__path__'):
    _strands_session_pkg.__path__ = []

_strands = sys.modules['strands']
_strands.Agent = MagicMock()
_strands.tool = MagicMock(side_effect=lambda f: f)
if not hasattr(_strands, '__path__'):
    _strands.__path__ = []

_strands_models = sys.modules['strands.models']
_strands_models.BedrockModel = MagicMock()
if not hasattr(_strands_models, '__path__'):
    _strands_models.__path__ = []

_bedrock = sys.modules['strands.models.bedrock']
_bedrock.BotocoreConfig = MagicMock()

_smcp = sys.modules['strands.tools.mcp.mcp_client']
_smcp.MCPClient = MagicMock()

_srm = sys.modules['strands.session.repository_session_manager']
_srm.RepositorySessionManager = MagicMock()


class _StubSessionRepository:
    pass


_ssr = sys.modules['strands.session.session_repository']
_ssr.SessionRepository = _StubSessionRepository

_strands_types_session = sys.modules['strands.types.session']
_strands_types_session.Session = MagicMock()
_strands_types_session.SessionAgent = MagicMock()
_strands_types_session.SessionMessage = MagicMock()
_strands_types_session.SessionType = MagicMock()

_mcp_client = sys.modules['mcp.client.streamable_http']
_mcp_client.streamablehttp_client = MagicMock()

# Provide a real HTTPException stub so PGScheduleService module-level code doesn't break
def _http_exc_init(self, status_code=500, detail=''):
    Exception.__init__(self, detail)
    self.status_code = status_code
    self.detail = detail

_fastapi = sys.modules['fastapi']
_fastapi.HTTPException = type('HTTPException', (Exception,), {'__init__': _http_exc_init})
_fastapi.exceptions = sys.modules['fastapi.exceptions']

# ---- app.utils.aws_config ---------------------------------------------------
# Stub this before any app module imports it so that PGScheduleService and
# other modules that call get_aws_region() at module level don't try to hit AWS.
if 'app.utils.aws_config' not in sys.modules:
    _aws_mod = types.ModuleType('app.utils.aws_config')
    _aws_mod.get_aws_region = lambda: 'us-east-1'
    _aws_mod.get_dynamodb_resource = MagicMock()
    _aws_mod.get_http_mcp_table = MagicMock()
    _aws_mod.get_chat_session_table = MagicMock()
    _aws_mod.get_chat_record_table = MagicMock()
    _aws_mod.get_orchestration_table = MagicMock()
    _aws_mod.get_agent_table = MagicMock()
    _aws_mod.get_user_table = MagicMock()
    _aws_mod.get_schedule_table = MagicMock()
    _aws_mod.get_config_table = MagicMock()
    _aws_mod.get_rest_api_registry_table = MagicMock()
    _aws_mod.DynamoDBTables = MagicMock()
    sys.modules['app.utils.aws_config'] = _aws_mod


# ---------------------------------------------------------------------------
# Session-scoped DB URL fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session')
def integration_db_url():
    """Return INTEGRATION_DATABASE_URL env var, or skip the entire session."""
    url = os.environ.get('INTEGRATION_DATABASE_URL')
    if not url:
        pytest.skip('INTEGRATION_DATABASE_URL not set — skipping integration tests')
    return url


# ---------------------------------------------------------------------------
# Session-scoped schema creation
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session', autouse=True)
def create_schema(integration_db_url):
    """Create all tables from schema.sql once per test session."""
    import psycopg2

    schema_path = os.path.join(_BE_DIR, 'db', 'schema.sql')
    with open(schema_path) as f:
        sql = f.read()

    conn = psycopg2.connect(integration_db_url)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.close()


# ---------------------------------------------------------------------------
# Function-scoped transaction connection
# ---------------------------------------------------------------------------

@pytest.fixture(scope='function')
def db_conn(integration_db_url):
    """
    Open a psycopg2 connection with autocommit=False.
    Every test runs inside this transaction; it is rolled back at teardown
    to leave the database clean.
    """
    import psycopg2

    conn = psycopg2.connect(integration_db_url)
    conn.autocommit = False
    yield conn
    conn.rollback()
    conn.close()


# ---------------------------------------------------------------------------
# _NoCommitConn — wraps the real connection but suppresses commit/rollback
# so that the test fixture (not the service) controls the transaction.
# ---------------------------------------------------------------------------

class _NoCommitConn:
    """Proxy for the real psycopg2 connection that swallows commit/rollback."""

    def __init__(self, real_conn):
        self._conn = real_conn

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        # Suppress: the test transaction will be rolled back by db_conn fixture
        pass

    def rollback(self):
        # Suppress: let the test fixture handle rollback
        pass


# ---------------------------------------------------------------------------
# pg_ctx — drop-in replacement for get_pg_connection
# ---------------------------------------------------------------------------

@pytest.fixture(scope='function')
def pg_ctx(db_conn):
    """
    Return a context-manager factory that yields a _NoCommitConn wrapping
    db_conn.  Patch this in place of get_pg_connection so all service DB
    calls share the same test transaction.
    """
    @contextmanager
    def _ctx():
        yield _NoCommitConn(db_conn)

    return _ctx


# ---------------------------------------------------------------------------
# Service fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='function')
def user_service(pg_ctx):
    """PGUserService with get_pg_connection patched to use the test transaction."""
    with patch('app.user.pg_user_service.get_pg_connection', pg_ctx):
        from app.user.pg_user_service import PGUserService
        yield PGUserService()


@pytest.fixture(scope='function')
def agent_service(pg_ctx):
    """PGAgentPOService with get_pg_connection patched to use the test transaction."""
    with patch('app.agent.pg_agent_service.get_pg_connection', pg_ctx):
        from app.agent.pg_agent_service import PGAgentPOService
        yield PGAgentPOService()


@pytest.fixture(scope='function')
def chat_service(pg_ctx):
    """
    PGChatRecordService with get_pg_connection patched.
    PostgreSQLSessionRepository.__init__ is also patched to avoid S3StorageService
    initialisation (which would try to connect to AWS).
    """
    with patch('app.agent.pg_agent_service.get_pg_connection', pg_ctx), \
         patch(
             'app.agent.pg_session_repository.S3StorageService',
             MagicMock,
         ):
        from app.agent.pg_agent_service import PGChatRecordService
        yield PGChatRecordService()


@pytest.fixture(scope='function')
def mcp_service(pg_ctx):
    """PGMCPService with get_pg_connection patched to use the test transaction."""
    with patch('app.mcp.pg_mcp_service.get_pg_connection', pg_ctx):
        from app.mcp.pg_mcp_service import PGMCPService
        yield PGMCPService()


@pytest.fixture(scope='function')
def config_service(pg_ctx):
    """PGConfigService with get_pg_connection patched to use the test transaction."""
    with patch('app.config.pg_config_service.get_pg_connection', pg_ctx):
        from app.config.pg_config_service import PGConfigService
        yield PGConfigService()


@pytest.fixture(scope='function')
def rest_api_registry(pg_ctx):
    """PGRestAPIRegistry with get_pg_connection patched to use the test transaction."""
    with patch('app.services.pg_rest_api_registry.get_pg_connection', pg_ctx):
        from app.services.pg_rest_api_registry import PGRestAPIRegistry
        yield PGRestAPIRegistry()
