"""
Unit tests for app/agent/pg_session_repository.py — PostgreSQLSessionRepository.

Before importing the target module we stub out:
  - strands.session.session_repository (SessionRepository base class)
  - strands.types.session (Session, SessionAgent, SessionMessage, SessionType)
  - strands.types.content
  - app.utils.s3_storage (S3StorageService)

All tests patch 'app.agent.pg_session_repository.get_pg_connection'.
"""
import sys
import json
import types
import base64
import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Stub strands session / types modules before importing the repository
# ---------------------------------------------------------------------------

for _mod_name in [
    'strands.types',
    'strands.types.session',
    'strands.types.content',
    'strands.session',
    'strands.session.session_repository',
]:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = types.ModuleType(_mod_name)


class _SessionRepository:
    """Minimal base class so PostgreSQLSessionRepository can inherit from it."""
    pass


sys.modules['strands.session.session_repository'].SessionRepository = _SessionRepository


class _SessionType:
    AGENT = MagicMock()
    AGENT.value = 'agent'


class _Session:
    def __init__(self, session_id='s1', session_type=None, created_at='', updated_at=''):
        self.session_id = session_id
        self.session_type = session_type or _SessionType.AGENT
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def from_dict(cls, d):
        obj = cls(session_id=d.get('session_id', 's1'))
        return obj

    def to_dict(self):
        return {
            'session_id': self.session_id,
            'session_type': self.session_type.value if hasattr(self.session_type, 'value') else self.session_type,
        }


class _SessionAgent:
    def __init__(self, agent_id='ag1', state=None, conversation_manager_state=None,
                 created_at='', updated_at=''):
        self.agent_id = agent_id
        self.state = state or {}
        self.conversation_manager_state = conversation_manager_state or {}
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def from_dict(cls, d):
        return cls(
            agent_id=d.get('agent_id', 'ag1'),
            state=d.get('state', {}),
            conversation_manager_state=d.get('conversation_manager_state', {}),
            created_at=d.get('created_at', ''),
            updated_at=d.get('updated_at', ''),
        )


class _SessionMessage:
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
_strands_types_session.Session = _Session
_strands_types_session.SessionAgent = _SessionAgent
_strands_types_session.SessionMessage = _SessionMessage
_strands_types_session.SessionType = _SessionType

# ---------------------------------------------------------------------------
# Stub app.utils.s3_storage
# ---------------------------------------------------------------------------

if 'app.utils.s3_storage' not in sys.modules:
    _s3_mod = types.ModuleType('app.utils.s3_storage')

    class _S3StorageService:
        def __init__(self):
            pass

        def upload_file(self, file_content=None, filename=None, **kwargs):
            return {'s3_key': 'test/key/file'}

        def get_encoded_file(self, s3key):
            return 'base64encodeddata'

        def get_file(self, s3key):
            return b'rawdata'

    _s3_mod.S3StorageService = _S3StorageService
    sys.modules['app.utils.s3_storage'] = _s3_mod
else:
    # Patch the class in the existing stub
    class _S3StorageService:
        def __init__(self):
            pass

        def upload_file(self, file_content=None, filename=None, **kwargs):
            return {'s3_key': 'test/key/file'}

        def get_encoded_file(self, s3key):
            return 'base64encodeddata'

        def get_file(self, s3key):
            return b'rawdata'

    sys.modules['app.utils.s3_storage'].S3StorageService = _S3StorageService


# ---------------------------------------------------------------------------
# Now import the module under test
# ---------------------------------------------------------------------------

from app.agent.pg_session_repository import PostgreSQLSessionRepository  # type: ignore

# ---------------------------------------------------------------------------
# Column layouts
# ---------------------------------------------------------------------------

SESSION_COLUMNS = ['session_id', 'session_type', 'created_at', 'updated_at']
SESSION_AGENT_COLUMNS = ['session_id', 'agent_id', 'state', 'conversation_manager_state',
                          'created_at', 'updated_at']
SESSION_MSG_COLUMNS = ['session_id', 'agent_id', 'message_id', 'message_content',
                        'created_at', 'updated_at']

SESSION_DESCRIPTION = [(col,) for col in SESSION_COLUMNS]
SESSION_AGENT_DESCRIPTION = [(col,) for col in SESSION_AGENT_COLUMNS]
SESSION_MSG_DESCRIPTION = [(col,) for col in SESSION_MSG_COLUMNS]

# ---------------------------------------------------------------------------
# Context-manager helpers
# ---------------------------------------------------------------------------

class _FakeCursor:
    def __init__(self, fetchone_val=None, fetchall_val=None, description=None):
        self.execute = MagicMock()
        self._fetchone_val = fetchone_val
        self._fetchall_val = fetchall_val or []
        self.description = description if description is not None else list(SESSION_MSG_DESCRIPTION)

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


PATCH_TARGET = 'app.agent.pg_session_repository.get_pg_connection'


def _make_svc():
    """Create a PostgreSQLSessionRepository with a mocked S3StorageService."""
    with patch('app.agent.pg_session_repository.S3StorageService') as mock_s3_cls:
        mock_s3 = MagicMock()
        mock_s3.upload_file.return_value = {'s3_key': 'test/key/file'}
        mock_s3.get_encoded_file.return_value = 'base64encodeddata'
        mock_s3_cls.return_value = mock_s3
        svc = PostgreSQLSessionRepository()
    return svc


# ===========================================================================
# create_session
# ===========================================================================

def test_create_session_executes_insert():
    svc = _make_svc()
    cur = _FakeCursor(description=list(SESSION_DESCRIPTION))
    session = _Session(session_id='s1')
    session.session_type = MagicMock()
    session.session_type.value = 'agent'
    session.created_at = '2024-01-01'
    session.updated_at = '2024-01-01'

    with patch(PATCH_TARGET, _pg(cur)):
        svc.create_session(session)
    cur.execute.assert_called_once()
    sql = cur.execute.call_args[0][0]
    assert 'chat_sessions' in sql.lower()
    assert 'INSERT' in sql.upper()


def test_create_session_returns_session():
    svc = _make_svc()
    cur = _FakeCursor(description=list(SESSION_DESCRIPTION))
    session = _Session(session_id='s1')
    session.session_type = MagicMock()
    session.session_type.value = 'agent'
    session.created_at = '2024-01-01'
    session.updated_at = '2024-01-01'

    with patch(PATCH_TARGET, _pg(cur)):
        result = svc.create_session(session)
    # create_session returns the same session object
    assert result is session


# ===========================================================================
# read_session
# ===========================================================================

def test_read_session_found():
    svc = _make_svc()
    row = ('s1', 'agent', '2024-01-01', '2024-01-01')
    cur = _FakeCursor(fetchone_val=row, description=list(SESSION_DESCRIPTION))

    with patch(PATCH_TARGET, _pg(cur)):
        session = svc.read_session('s1')
    assert session is not None
    assert session.session_id == 's1'


def test_read_session_not_found():
    svc = _make_svc()
    cur = _FakeCursor(fetchone_val=None, description=list(SESSION_DESCRIPTION))

    with patch(PATCH_TARGET, _pg(cur)):
        session = svc.read_session('missing')
    assert session is None


# ===========================================================================
# create_agent
# ===========================================================================

def test_create_agent_executes_insert():
    svc = _make_svc()
    cur = _FakeCursor(description=list(SESSION_AGENT_DESCRIPTION))
    agent = _SessionAgent(agent_id='ag1', state={}, conversation_manager_state={},
                          created_at='2024-01-01', updated_at='2024-01-01')

    with patch(PATCH_TARGET, _pg(cur)):
        svc.create_agent('s1', agent)
    cur.execute.assert_called_once()
    sql = cur.execute.call_args[0][0]
    assert 'session_agents' in sql.lower()
    assert 'INSERT' in sql.upper()


# ===========================================================================
# read_agent
# ===========================================================================

def test_read_agent_found():
    svc = _make_svc()
    row = ('s1', 'ag1', '{}', '{}', '2024-01-01', '2024-01-01')
    cur = _FakeCursor(fetchone_val=row, description=list(SESSION_AGENT_DESCRIPTION))

    with patch(PATCH_TARGET, _pg(cur)):
        agent = svc.read_agent('s1', 'ag1')
    assert agent is not None
    assert agent.agent_id == 'ag1'


def test_read_agent_not_found():
    svc = _make_svc()
    cur = _FakeCursor(fetchone_val=None, description=list(SESSION_AGENT_DESCRIPTION))

    with patch(PATCH_TARGET, _pg(cur)):
        agent = svc.read_agent('s1', 'missing')
    assert agent is None


# ===========================================================================
# update_agent
# ===========================================================================

def test_update_agent_upserts():
    svc = _make_svc()
    cur = _FakeCursor(description=list(SESSION_AGENT_DESCRIPTION))
    agent = _SessionAgent(agent_id='ag1', state={'k': 'v'}, conversation_manager_state={},
                          created_at='2024-01-01', updated_at='2024-01-01')

    with patch(PATCH_TARGET, _pg(cur)):
        svc.update_agent('s1', agent)
    cur.execute.assert_called_once()
    sql = cur.execute.call_args[0][0]
    assert 'ON CONFLICT' in sql.upper()
    assert 'session_agents' in sql.lower()


# ===========================================================================
# create_message
# ===========================================================================

def _make_simple_message(message_id=1):
    msg = _SessionMessage(
        message_id=message_id,
        message={'role': 'user', 'content': [{'text': 'hello'}]},
        created_at='2024-01-01',
        updated_at='2024-01-01',
    )
    return msg


def test_create_message_executes_insert():
    svc = _make_svc()
    cur = _FakeCursor(description=list(SESSION_MSG_DESCRIPTION))
    session_msg = _make_simple_message(message_id=1)

    with patch(PATCH_TARGET, _pg(cur)):
        svc.create_message('s1', 'ag1', session_msg)
    cur.execute.assert_called_once()
    sql = cur.execute.call_args[0][0]
    assert 'session_messages' in sql.lower()
    assert 'INSERT' in sql.upper()


def test_create_message_with_s3_upload_for_image():
    """Messages containing image content blocks trigger an S3 upload."""
    with patch('app.agent.pg_session_repository.S3StorageService') as mock_s3_cls:
        mock_s3 = MagicMock()
        mock_s3.upload_file.return_value = {'s3_key': 'test/key/img'}
        mock_s3_cls.return_value = mock_s3
        svc = PostgreSQLSessionRepository()

    # Build a valid base64-encoded image
    raw_bytes = b'fakeimagebytes'
    b64_data = base64.b64encode(raw_bytes).decode()

    msg = _SessionMessage(
        message_id=1,
        message={
            'role': 'user',
            'content': [{
                'image': {
                    'source': {
                        'bytes': {'data': b64_data},
                    }
                }
            }]
        },
        created_at='2024-01-01',
        updated_at='2024-01-01',
    )

    cur = _FakeCursor(description=list(SESSION_MSG_DESCRIPTION))
    with patch(PATCH_TARGET, _pg(cur)):
        svc.create_message('s1', 'ag1', msg)

    svc.s3_storage.upload_file.assert_called_once()
    cur.execute.assert_called_once()


# ===========================================================================
# read_message
# ===========================================================================

def test_read_message_found():
    svc = _make_svc()
    message_dict = {'message_id': 1, 'message': {'role': 'user', 'content': []},
                    'created_at': '2024-01-01', 'updated_at': '2024-01-01'}
    row = ('s1', 'ag1', 1, json.dumps(message_dict), '2024-01-01', '2024-01-01')
    cur = _FakeCursor(fetchone_val=row, description=list(SESSION_MSG_DESCRIPTION))

    with patch(PATCH_TARGET, _pg(cur)):
        msg = svc.read_message('s1', 'ag1', 1)
    assert msg is not None
    assert msg.message_id == 1


def test_read_message_not_found():
    svc = _make_svc()
    cur = _FakeCursor(fetchone_val=None, description=list(SESSION_MSG_DESCRIPTION))

    with patch(PATCH_TARGET, _pg(cur)):
        msg = svc.read_message('s1', 'ag1', 999)
    assert msg is None


def test_read_message_downloads_image_from_s3():
    """If message_content has an s3key, read_message fetches from S3."""
    with patch('app.agent.pg_session_repository.S3StorageService') as mock_s3_cls:
        mock_s3 = MagicMock()
        mock_s3.get_encoded_file.return_value = 'base64imagedata'
        mock_s3_cls.return_value = mock_s3
        svc = PostgreSQLSessionRepository()

    message_dict = {
        'message_id': 1,
        'message': {
            'role': 'user',
            'content': [{
                'image': {
                    'source': {
                        's3key': 'some/s3/key',
                        'bytes': {'data': ''},
                    }
                }
            }]
        },
        'created_at': '2024-01-01',
        'updated_at': '2024-01-01',
    }
    row = ('s1', 'ag1', 1, json.dumps(message_dict), '2024-01-01', '2024-01-01')
    cur = _FakeCursor(fetchone_val=row, description=list(SESSION_MSG_DESCRIPTION))

    with patch(PATCH_TARGET, _pg(cur)):
        msg = svc.read_message('s1', 'ag1', 1)

    svc.s3_storage.get_encoded_file.assert_called_once_with('some/s3/key')
    assert msg is not None


# ===========================================================================
# update_message
# ===========================================================================

def test_update_message_executes_update():
    svc = _make_svc()
    cur = _FakeCursor(description=list(SESSION_MSG_DESCRIPTION))
    msg = _make_simple_message(message_id=1)

    with patch(PATCH_TARGET, _pg(cur)):
        svc.update_message('s1', 'ag1', msg)
    cur.execute.assert_called_once()
    sql = cur.execute.call_args[0][0]
    assert 'UPDATE' in sql.upper()
    assert 'session_messages' in sql.lower()


# ===========================================================================
# list_messages
# ===========================================================================

def _msg_row(message_id=1, content=None):
    if content is None:
        content = {'message_id': message_id,
                   'message': {'role': 'assistant', 'content': []},
                   'created_at': '2024-01-01', 'updated_at': '2024-01-01'}
    return ('s1', 'ag1', message_id, json.dumps(content), '2024-01-01', '2024-01-01')


def test_list_messages_no_limit():
    svc = _make_svc()
    rows = [_msg_row(1), _msg_row(2)]
    cur = _FakeCursor(fetchall_val=rows, description=list(SESSION_MSG_DESCRIPTION))

    with patch(PATCH_TARGET, _pg(cur)):
        msgs = svc.list_messages('s1', 'ag1')
    assert len(msgs) == 2
    # Verify OFFSET used (no LIMIT)
    sql = cur.execute.call_args[0][0]
    assert 'LIMIT' not in sql.upper()
    assert 'OFFSET' in sql.upper()


def test_list_messages_with_limit():
    svc = _make_svc()
    rows = [_msg_row(1)]
    cur = _FakeCursor(fetchall_val=rows, description=list(SESSION_MSG_DESCRIPTION))

    with patch(PATCH_TARGET, _pg(cur)):
        msgs = svc.list_messages('s1', 'ag1', limit=1)
    assert len(msgs) == 1
    sql = cur.execute.call_args[0][0]
    assert 'LIMIT' in sql.upper()


def test_list_messages_handles_parse_error_gracefully():
    """A row with invalid JSON message_content should be skipped."""
    svc = _make_svc()
    bad_row = ('s1', 'ag1', 1, 'NOT_VALID_JSON', '2024-01-01', '2024-01-01')
    good_row = _msg_row(2)
    cur = _FakeCursor(fetchall_val=[bad_row, good_row], description=list(SESSION_MSG_DESCRIPTION))

    with patch(PATCH_TARGET, _pg(cur)):
        msgs = svc.list_messages('s1', 'ag1')
    # The bad row should be skipped; only the good row parsed
    assert len(msgs) == 1


def test_list_messages_with_s3_attachment_read():
    """When read_attachment=True, s3key triggers a download."""
    with patch('app.agent.pg_session_repository.S3StorageService') as mock_s3_cls:
        mock_s3 = MagicMock()
        mock_s3.get_encoded_file.return_value = 'base64imagedata'
        mock_s3_cls.return_value = mock_s3
        svc = PostgreSQLSessionRepository()

    content = {
        'message_id': 1,
        'message': {
            'role': 'user',
            'content': [{
                'image': {
                    'source': {
                        's3key': 'some/s3/key',
                        'bytes': {'data': ''},
                    }
                }
            }]
        },
        'created_at': '2024-01-01',
        'updated_at': '2024-01-01',
    }
    row = ('s1', 'ag1', 1, json.dumps(content), '2024-01-01', '2024-01-01')
    cur = _FakeCursor(fetchall_val=[row], description=list(SESSION_MSG_DESCRIPTION))

    with patch(PATCH_TARGET, _pg(cur)):
        msgs = svc.list_messages('s1', 'ag1', read_attachment=True)

    svc.s3_storage.get_encoded_file.assert_called_once_with('some/s3/key')
    assert len(msgs) == 1
