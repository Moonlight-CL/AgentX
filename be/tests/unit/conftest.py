"""
Unit-test conftest: adds the be/ directory to sys.path and pre-patches
heavy AWS/boto3/FastAPI/psycopg2 imports so that app modules can be
imported without live AWS credentials or a real database.
"""
import sys
import os

# Ensure the 'be/' directory (parent of 'app/') is on the path so that
# 'import app.xxx' works from every unit test file.
_BE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _BE_DIR not in sys.path:
    sys.path.insert(0, _BE_DIR)

# ---------------------------------------------------------------------------
# Stub out all heavy third-party modules before any app module is imported.
# ---------------------------------------------------------------------------
from unittest.mock import MagicMock  # noqa: E402
import types  # noqa: E402


def _make_stub(name: str) -> types.ModuleType:
    """Return a minimal module stub."""
    mod = types.ModuleType(name)
    mod.__spec__ = None
    return mod


# ---- psycopg2 ---------------------------------------------------------------
# pg_config.py does 'import psycopg2' and 'from psycopg2 import pool' at
# module level, so we need both the top-level module and its sub-modules.
for _mod_name in ['psycopg2', 'psycopg2.pool', 'psycopg2.extras']:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _make_stub(_mod_name)

_psycopg2 = sys.modules['psycopg2']
_psycopg2.pool = sys.modules['psycopg2.pool']
_psycopg2.extras = sys.modules['psycopg2.extras']
_psycopg2.pool.ThreadedConnectionPool = MagicMock()

# ---- FastAPI ----------------------------------------------------------------
# schedule/service.py (imported by schedule/__init__.py) uses FastAPI's
# HTTPException at module level.
for _mod_name in ['fastapi', 'fastapi.exceptions']:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _make_stub(_mod_name)

def _http_exc_init(self, status_code=500, detail=''):
    Exception.__init__(self, detail)
    self.status_code = status_code
    self.detail = detail

_fastapi = sys.modules['fastapi']
_fastapi.HTTPException = type('HTTPException', (Exception,), {'__init__': _http_exc_init})
_fastapi.exceptions = sys.modules['fastapi.exceptions']

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

# botocore needs __path__ so sub-module imports work
_botocore = sys.modules['botocore']
if not hasattr(_botocore, '__path__'):
    _botocore.__path__ = []

# Stub ClientError used by s3_storage
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
]:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _make_stub(_mod_name)

# Make strands.session behave like a package so sub-module imports work.
_strands_session_pkg = sys.modules['strands.session']
if not hasattr(_strands_session_pkg, '__path__'):
    _strands_session_pkg.__path__ = []

_strands = sys.modules['strands']
_strands.Agent = MagicMock()
_strands.tool = MagicMock(side_effect=lambda f: f)  # transparent decorator
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

# Stub SessionRepository base class used by pg_session_repository.
class _StubSessionRepository:
    pass

_ssr = sys.modules['strands.session.session_repository']
_ssr.SessionRepository = _StubSessionRepository

# Stub strands.types.session classes used by dynamodb_session_repository and
# pg_session_repository.
class _StubSession:
    def __init__(self, session_id='', session_type=None, created_at='', updated_at=''):
        self.session_id = session_id
        self.session_type = session_type or MagicMock(value='agent')
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def from_dict(cls, d):
        return cls(session_id=d.get('session_id', ''))


class _StubSessionAgent:
    def __init__(self, agent_id='', state=None, conversation_manager_state=None,
                 created_at='', updated_at=''):
        self.agent_id = agent_id
        self.state = state or {}
        self.conversation_manager_state = conversation_manager_state or {}
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def from_dict(cls, d):
        return cls(
            agent_id=d.get('agent_id', ''),
            state=d.get('state', {}),
            conversation_manager_state=d.get('conversation_manager_state', {}),
            created_at=d.get('created_at', ''),
            updated_at=d.get('updated_at', ''),
        )


class _StubSessionMessage:
    def __init__(self, message_id=0, message=None, created_at='', updated_at=''):
        self.message_id = message_id
        self.message = message or {}
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def from_dict(cls, d):
        return cls(
            message_id=d.get('message_id', 0),
            message=d.get('message', {}),
            created_at=d.get('created_at', ''),
            updated_at=d.get('updated_at', ''),
        )

    def to_dict(self):
        return {
            'message_id': self.message_id,
            'message': self.message,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


_strands_types_session = sys.modules['strands.types.session']
_strands_types_session.Session = _StubSession
_strands_types_session.SessionAgent = _StubSessionAgent
_strands_types_session.SessionMessage = _StubSessionMessage
_strands_types_session.SessionType = MagicMock()

_mcp_client = sys.modules['mcp.client.streamable_http']
_mcp_client.streamablehttp_client = MagicMock()

# ---- pydantic ---------------------------------------------------------------
# pydantic is a real install we can use; nothing to stub.

# ---- httpx ------------------------------------------------------------------
for _mod_name in ['httpx']:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _make_stub(_mod_name)
