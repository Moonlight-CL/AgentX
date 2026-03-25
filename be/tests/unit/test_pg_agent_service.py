"""
Unit tests for app/agent/pg_agent_service.py — PGAgentPOService and PGChatRecordService.

All tests patch 'app.agent.pg_agent_service.get_pg_connection' so that no real
database is required. PGChatRecordService.__init__ imports
PostgreSQLSessionRepository, so that is also patched at the module level.
"""
import json
import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Column layouts (must match SELECT * column order in the source)
# ---------------------------------------------------------------------------

AGENT_COLUMNS = [
    'user_id', 'id', 'name', 'display_name', 'description', 'agent_type',
    'model_provider', 'model_id', 'sys_prompt', 'tools', 'envs', 'extras',
    'shared_users', 'shared_groups', 'is_public', 'creator', 'runtime',
]

CHAT_COLUMNS = [
    'user_id', 'id', 'agent_id', 'user_message', 'create_time',
    'record_type', 'config', 'status', 'end_time', 'results', 'error',
]

AGENT_DESCRIPTION = [(col,) for col in AGENT_COLUMNS]
CHAT_DESCRIPTION = [(col,) for col in CHAT_COLUMNS]

# ---------------------------------------------------------------------------
# Row helpers
# ---------------------------------------------------------------------------

def _agent_row(**overrides):
    defaults = {
        'user_id': 'u1', 'id': 'a1', 'name': 'MyAgent',
        'display_name': 'My Agent', 'description': 'desc',
        'agent_type': 1, 'model_provider': 1,
        'model_id': 'us.anthropic.claude-3-7-sonnet', 'sys_prompt': 'You are helpful',
        'tools': '[]', 'envs': '', 'extras': None,
        'shared_users': '[]', 'shared_groups': '[]',
        'is_public': False, 'creator': 'u1', 'runtime': 1,
    }
    defaults.update(overrides)
    return defaults


def _agent_tuple(d):
    return tuple(d[c] for c in AGENT_COLUMNS)


def _chat_row(**overrides):
    defaults = {
        'user_id': 'u1', 'id': 'c1', 'agent_id': 'a1',
        'user_message': 'hello', 'create_time': '2024-01-01T00:00:00',
        'record_type': 'agent', 'config': None, 'status': None,
        'end_time': None, 'results': None, 'error': None,
    }
    defaults.update(overrides)
    return defaults


def _chat_tuple(d):
    return tuple(d[c] for c in CHAT_COLUMNS)


# ---------------------------------------------------------------------------
# Context-manager mock helpers
# ---------------------------------------------------------------------------

class _FakeAgentCursor:
    """Cursor that supports sequential fetchone() calls (returns items from a list)."""
    def __init__(self, fetchone_val=None, fetchall_val=None, fetchone_seq=None):
        self.execute = MagicMock()
        self._fetchone_seq = list(fetchone_seq) if fetchone_seq is not None else [fetchone_val]
        self._fetchone_idx = 0
        self._fetchall_val = fetchall_val or []
        self.description = list(AGENT_DESCRIPTION)

    def fetchone(self):
        if self._fetchone_idx < len(self._fetchone_seq):
            val = self._fetchone_seq[self._fetchone_idx]
            self._fetchone_idx += 1
            return val
        return None

    def fetchall(self):
        return self._fetchall_val

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


class _FakeChatCursor:
    """Cursor that supports sequential fetchone() and fetchall() calls."""
    def __init__(self, fetchone_val=None, fetchall_val=None, fetchone_seq=None, fetchall_seq=None):
        self.execute = MagicMock()
        self._fetchone_seq = list(fetchone_seq) if fetchone_seq is not None else [fetchone_val]
        self._fetchone_idx = 0
        if fetchall_seq is not None:
            self._fetchall_seq = list(fetchall_seq)
        else:
            self._fetchall_seq = [fetchall_val or []]
        self._fetchall_idx = 0
        self.description = list(CHAT_DESCRIPTION)

    def fetchone(self):
        if self._fetchone_idx < len(self._fetchone_seq):
            val = self._fetchone_seq[self._fetchone_idx]
            self._fetchone_idx += 1
            return val
        return None

    def fetchall(self):
        if self._fetchall_idx < len(self._fetchall_seq):
            val = self._fetchall_seq[self._fetchall_idx]
            self._fetchall_idx += 1
            return val
        return []

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


AGENT_PATCH = 'app.agent.pg_agent_service.get_pg_connection'
# PGChatRecordService.__init__ does 'from .pg_session_repository import PostgreSQLSessionRepository'
# so we patch the name on the pg_session_repository module.
SESSION_REPO_PATCH = 'app.agent.pg_session_repository.PostgreSQLSessionRepository'

# ---------------------------------------------------------------------------
# Imports (after conftest stubs are in place)
# ---------------------------------------------------------------------------

from app.agent.pg_agent_service import PGAgentPOService, PGChatRecordService  # type: ignore
from app.agent.agent import (  # type: ignore
    AgentPO, AgentType, AgentTool, AgentToolType, AgentRuntime, ModelProvider,
    ChatRecord, ChatResponse,
)


# ===========================================================================
# Helper: build a minimal valid AgentPO
# ===========================================================================

def _make_agent_po(**overrides):
    defaults = dict(
        id='a1', name='MyAgent', display_name='My Agent', description='desc',
        agent_type=AgentType.plain, model_provider=ModelProvider.bedrock,
        model_id='us.anthropic.claude-3-7-sonnet',
        sys_prompt='You are helpful', tools=[], envs='',
        extras=None, shared_users=None, shared_groups=None,
        is_public=False, creator='u1', runtime=AgentRuntime.local,
    )
    defaults.update(overrides)
    return AgentPO(**defaults)


def _make_chat_record(**overrides):
    defaults = dict(
        id='c1', agent_id='a1', user_id='u1', user_message='hello',
        create_time='2024-01-01T00:00:00', record_type='agent',
    )
    defaults.update(overrides)
    return ChatRecord(**defaults)


# ===========================================================================
# PGAgentPOService tests
# ===========================================================================

class TestAddAgent:
    def test_add_agent_executes_insert(self):
        cur = _FakeAgentCursor()
        agent = _make_agent_po()
        with patch(AGENT_PATCH, _pg(cur)):
            PGAgentPOService().add_agent(agent, user_id='u1')
        cur.execute.assert_called_once()
        sql = cur.execute.call_args[0][0]
        assert 'agents' in sql.lower()
        assert 'INSERT' in sql.upper()

    def test_add_agent_raises_for_non_agentpo(self):
        with pytest.raises(TypeError):
            PGAgentPOService().add_agent("not an AgentPO")

    def test_add_agent_with_extras(self):
        cur = _FakeAgentCursor()
        agent = _make_agent_po(extras={'key': 'val'})
        with patch(AGENT_PATCH, _pg(cur)):
            PGAgentPOService().add_agent(agent, user_id='u1')
        cur.execute.assert_called_once()
        args = cur.execute.call_args[0][1]
        # extras should be json.dumps({'key': 'val'})
        assert json.dumps({'key': 'val'}) in args


class TestGetAgent:
    def test_get_agent_found_in_user_space(self):
        row = _agent_tuple(_agent_row())
        cur = _FakeAgentCursor(fetchone_val=row)
        with patch(AGENT_PATCH, _pg(cur)):
            agent = PGAgentPOService().get_agent('u1', 'a1')
        assert agent is not None
        assert agent.id == 'a1'
        assert agent.name == 'MyAgent'

    def test_get_agent_found_in_public(self):
        # get_agent uses ONE connection, ONE cursor; fetchone() called twice in loop
        # first call returns None (user-space), second returns row (public)
        row = _agent_tuple(_agent_row(user_id='public'))
        cur = _FakeAgentCursor(fetchone_seq=[None, row])
        with patch(AGENT_PATCH, _pg(cur)):
            agent = PGAgentPOService().get_agent('u1', 'a1')
        assert agent is not None

    def test_get_agent_not_found(self):
        cur = _FakeAgentCursor(fetchone_val=None)
        with patch(AGENT_PATCH, _pg(cur)):
            agent = PGAgentPOService().get_agent('u1', 'missing')
        assert agent is None


class TestListAgents:
    def test_list_agents_returns_sorted_list(self):
        rows = [
            _agent_tuple(_agent_row(id='a2', name='Zebra')),
            _agent_tuple(_agent_row(id='a1', name='Apple')),
        ]
        cur = _FakeAgentCursor(fetchall_val=rows)
        with patch(AGENT_PATCH, _pg(cur)):
            agents = PGAgentPOService().list_agents('u1')
        assert len(agents) == 2
        assert agents[0].name == 'Apple'
        assert agents[1].name == 'Zebra'

    def test_list_agents_empty(self):
        cur = _FakeAgentCursor(fetchall_val=[])
        with patch(AGENT_PATCH, _pg(cur)):
            agents = PGAgentPOService().list_agents('u1')
        assert agents == []

    def test_list_agents_error_returns_empty(self):
        @contextmanager
        def _boom():
            raise RuntimeError('db error')
            yield  # noqa

        with patch(AGENT_PATCH, _boom):
            agents = PGAgentPOService().list_agents('u1')
        assert agents == []


class TestDeleteAgent:
    def test_delete_agent_success(self):
        cur = _FakeAgentCursor()
        with patch(AGENT_PATCH, _pg(cur)):
            result = PGAgentPOService().delete_agent('u1', 'a1')
        assert result is True

    def test_delete_agent_error(self):
        @contextmanager
        def _boom():
            raise RuntimeError('db error')
            yield  # noqa

        with patch(AGENT_PATCH, _boom):
            result = PGAgentPOService().delete_agent('u1', 'a1')
        assert result is False


class TestUpdateAgentSharing:
    def test_update_agent_sharing_not_found(self):
        # get_agent returns None → both fetchone calls return None
        cur = _FakeAgentCursor(fetchone_val=None)
        with patch(AGENT_PATCH, _pg(cur)):
            ok, msg = PGAgentPOService().update_agent_sharing('u1', 'missing')
        assert ok is False
        assert 'not found' in msg.lower() or 'permission' in msg.lower()

    def test_update_agent_sharing_no_fields(self):
        # get_agent succeeds, but no sharing fields provided
        row = _agent_tuple(_agent_row())
        cur = _FakeAgentCursor(fetchone_val=row)
        with patch(AGENT_PATCH, _pg(cur)):
            ok, msg = PGAgentPOService().update_agent_sharing('u1', 'a1')
        assert ok is True
        assert msg == ""

    def test_update_agent_sharing_is_public(self):
        row = _agent_tuple(_agent_row())
        update_cur = _FakeAgentCursor()
        call_idx = [0]

        @contextmanager
        def _ctx():
            if call_idx[0] == 0:
                # get_agent connection
                cur = _FakeAgentCursor(fetchone_val=row)
            else:
                # update connection
                cur = _FakeAgentCursor()
            call_idx[0] += 1
            yield _FakeConn(cur)

        with patch(AGENT_PATCH, _ctx):
            ok, msg = PGAgentPOService().update_agent_sharing('u1', 'a1', is_public=True)
        assert ok is True
        assert msg == ""

    def test_update_agent_sharing_error(self):
        row = _agent_tuple(_agent_row())
        call_idx = [0]

        @contextmanager
        def _ctx():
            if call_idx[0] == 0:
                cur = _FakeAgentCursor(fetchone_val=row)
                call_idx[0] += 1
                yield _FakeConn(cur)
            else:
                raise RuntimeError('update failed')
                yield  # noqa

        with patch(AGENT_PATCH, _ctx):
            ok, msg = PGAgentPOService().update_agent_sharing('u1', 'a1', is_public=True)
        assert ok is False
        assert 'update failed' in msg


class TestMakeAgentPublic:
    def test_make_agent_public_success(self):
        cur = _FakeAgentCursor()
        with patch(AGENT_PATCH, _pg(cur)):
            result = PGAgentPOService().make_agent_public('a1')
        assert result is True

    def test_make_agent_public_error(self):
        @contextmanager
        def _boom():
            raise RuntimeError('db error')
            yield  # noqa

        with patch(AGENT_PATCH, _boom):
            result = PGAgentPOService().make_agent_public('a1')
        assert result is False


class TestGetAgentSharingInfo:
    def test_get_agent_sharing_info_found(self):
        row = _agent_tuple(_agent_row(shared_users='["user2"]', shared_groups='["grp1"]', is_public=True))
        cur = _FakeAgentCursor(fetchone_val=row)
        with patch(AGENT_PATCH, _pg(cur)):
            info, err = PGAgentPOService().get_agent_sharing_info('u1', 'a1')
        assert err == ""
        assert info is not None
        assert info['is_public'] is True
        assert 'shared_users' in info
        assert 'shared_groups' in info

    def test_get_agent_sharing_info_not_found(self):
        cur = _FakeAgentCursor(fetchone_val=None)
        with patch(AGENT_PATCH, _pg(cur)):
            info, err = PGAgentPOService().get_agent_sharing_info('u1', 'missing')
        assert info is None
        assert err != ""


class TestMapPgAgent:
    def _svc(self):
        return PGAgentPOService()

    def test_map_pg_agent_basic(self):
        svc = self._svc()
        item = _agent_row()
        agent = svc._map_pg_agent(item)
        assert agent.id == 'a1'
        assert agent.name == 'MyAgent'
        assert agent.agent_type == AgentType.plain
        assert agent.runtime == AgentRuntime.local
        assert agent.tools == []

    def test_map_pg_agent_invalid_agent_type_defaults_to_plain(self):
        svc = self._svc()
        item = _agent_row(agent_type=99)
        agent = svc._map_pg_agent(item)
        assert agent.agent_type == AgentType.plain

    def test_map_pg_agent_tools_are_parsed(self):
        svc = self._svc()
        # AgentToolType is an Enum with integer values: strands=1, mcp=2, agent=3, python=4
        tool_data = {
            'name': 'calculator',
            'display_name': 'Calculator',
            'category': 'Utilities',
            'desc': 'Perform calculations',
            'type': 1,  # integer value for AgentToolType.strands
        }
        tools_json = json.dumps([json.dumps(tool_data)])
        item = _agent_row(tools=tools_json)
        agent = svc._map_pg_agent(item)
        assert len(agent.tools) == 1
        assert agent.tools[0].name == 'calculator'

    def test_map_pg_agent_json_string_extras(self):
        svc = self._svc()
        extras = {'foo': 'bar'}
        item = _agent_row(extras=json.dumps(extras))
        agent = svc._map_pg_agent(item)
        assert agent.extras == extras

    def test_map_pg_agent_json_string_shared_users(self):
        svc = self._svc()
        item = _agent_row(shared_users='["user2","user3"]')
        agent = svc._map_pg_agent(item)
        assert agent.shared_users == ['user2', 'user3']


# ===========================================================================
# PGChatRecordService tests
# ===========================================================================

class TestAddChatRecord:
    def _svc(self):
        with patch(SESSION_REPO_PATCH) as mock_cls:
            mock_cls.return_value = MagicMock()
            svc = PGChatRecordService()
        return svc

    def test_add_chat_record_executes_insert(self):
        svc = self._svc()
        cur = _FakeChatCursor()
        record = _make_chat_record(id='c1')
        with patch(AGENT_PATCH, _pg(cur)):
            svc.add_chat_record(record)
        cur.execute.assert_called_once()
        sql = cur.execute.call_args[0][0]
        assert 'chat_records' in sql.lower()
        assert 'INSERT' in sql.upper()

    def test_add_chat_record_auto_generates_id(self):
        svc = self._svc()
        cur = _FakeChatCursor()
        record = _make_chat_record(id='')
        with patch(AGENT_PATCH, _pg(cur)):
            svc.add_chat_record(record)
        # id should have been set
        assert record.id != ''
        assert len(record.id) == 32  # uuid4().hex

    def test_add_chat_record_with_config_and_results(self):
        svc = self._svc()
        cur = _FakeChatCursor()
        record = _make_chat_record(
            id='c1',
            config={'model': 'gpt-4'},
            results={'output': 'done'},
        )
        with patch(AGENT_PATCH, _pg(cur)):
            svc.add_chat_record(record)
        cur.execute.assert_called_once()
        args = cur.execute.call_args[0][1]
        # config and results should be JSON serialized
        assert json.dumps({'model': 'gpt-4'}) in args
        assert json.dumps({'output': 'done'}) in args


class TestGetChatRecord:
    def _svc(self):
        with patch(SESSION_REPO_PATCH) as mock_cls:
            mock_cls.return_value = MagicMock()
            svc = PGChatRecordService()
        return svc

    def test_get_chat_record_found(self):
        svc = self._svc()
        row = _chat_tuple(_chat_row())
        # get_chat_record uses ONE connection, ONE cursor, calls fetchone twice (user then public)
        cur = _FakeChatCursor(fetchone_seq=[row, None])
        with patch(AGENT_PATCH, _pg(cur)):
            record = svc.get_chat_record('u1', 'c1')
        assert record is not None
        assert record.id == 'c1'
        assert record.user_message == 'hello'

    def test_get_chat_record_not_found(self):
        svc = self._svc()
        cur = _FakeChatCursor(fetchone_seq=[None, None])
        with patch(AGENT_PATCH, _pg(cur)):
            record = svc.get_chat_record('u1', 'missing')
        assert record is None


class TestGetChatRecordsByUser:
    def _svc(self):
        with patch(SESSION_REPO_PATCH) as mock_cls:
            mock_cls.return_value = MagicMock()
            svc = PGChatRecordService()
        return svc

    def test_get_chat_records_by_user_returns_sorted(self):
        svc = self._svc()
        # get_chat_records_by_user uses ONE connection, ONE cursor, calls fetchall twice
        rows_user = [
            _chat_tuple(_chat_row(id='c2', create_time='2024-01-02T00:00:00')),
        ]
        rows_public = [
            _chat_tuple(_chat_row(id='c1', user_id='public', create_time='2024-01-01T00:00:00')),
        ]
        cur = _FakeChatCursor(fetchall_seq=[rows_user, rows_public])
        with patch(AGENT_PATCH, _pg(cur)):
            records = svc.get_chat_records_by_user('u1')

        assert len(records) == 2
        # sorted desc by create_time
        assert records[0].create_time >= records[1].create_time

    def test_get_chat_records_by_user_with_record_type_filter(self):
        svc = self._svc()
        rows = [_chat_tuple(_chat_row(record_type='orchestration'))]
        cur = _FakeChatCursor(fetchall_seq=[rows, []])
        with patch(AGENT_PATCH, _pg(cur)):
            records = svc.get_chat_records_by_user('u1', record_type='orchestration')

        assert len(records) == 1
        assert records[0].record_type == 'orchestration'


class TestGetRecordsByAgentId:
    def _svc(self):
        with patch(SESSION_REPO_PATCH) as mock_cls:
            mock_cls.return_value = MagicMock()
            svc = PGChatRecordService()
        return svc

    def test_get_records_by_agent_id(self):
        svc = self._svc()
        # Uses ONE connection, ONE cursor, calls fetchall twice (user_id then public)
        rows = [_chat_tuple(_chat_row(agent_id='agent-x'))]
        cur = _FakeChatCursor(fetchall_seq=[rows, []])
        with patch(AGENT_PATCH, _pg(cur)):
            records = svc.get_records_by_agent_id('u1', 'agent-x')
        assert len(records) == 1

    def test_get_records_by_agent_id_with_record_type(self):
        svc = self._svc()
        rows = [_chat_tuple(_chat_row(agent_id='agent-x', record_type='agent'))]
        cur = _FakeChatCursor(fetchall_seq=[rows, []])
        with patch(AGENT_PATCH, _pg(cur)):
            records = svc.get_records_by_agent_id('u1', 'agent-x', record_type='agent')
        assert len(records) == 1
        assert records[0].record_type == 'agent'


class TestChatResponseMethods:
    def _svc(self):
        with patch(SESSION_REPO_PATCH) as mock_cls:
            mock_cls.return_value = MagicMock()
            svc = PGChatRecordService()
        return svc

    def test_add_chat_response_is_noop(self):
        svc = self._svc()
        # Should not raise; returns None
        result = svc.add_chat_response(MagicMock())
        assert result is None

    def test_get_all_chat_responses_returns_empty(self):
        svc = self._svc()
        result = svc.get_all_chat_responses('c1')
        assert result == []

    def test_get_all_chat_responses_from_session_success(self):
        with patch(SESSION_REPO_PATCH) as mock_cls:
            mock_repo = MagicMock()
            mock_cls.return_value = mock_repo
            svc = PGChatRecordService()

        # Build fake SessionMessage-like objects
        msg1 = MagicMock()
        msg1.to_dict.return_value = {'role': 'assistant', 'content': 'hi'}
        msg1.created_at = '2024-01-01T00:00:00'
        mock_repo.list_messages.return_value = [msg1]

        responses = svc.get_all_chat_responses_from_session('chat-1', 'agent-1')
        assert len(responses) == 1
        assert responses[0].chat_id == 'chat-1'
        assert responses[0].resp_no == 0
        mock_repo.list_messages.assert_called_once_with(
            session_id='chat-1', agent_id='agent-1_chat-1', read_attachment=False
        )

    def test_get_all_chat_responses_from_session_error(self):
        with patch(SESSION_REPO_PATCH) as mock_cls:
            mock_repo = MagicMock()
            mock_repo.list_messages.side_effect = RuntimeError('session error')
            mock_cls.return_value = mock_repo
            svc = PGChatRecordService()

        responses = svc.get_all_chat_responses_from_session('chat-1', 'agent-1')
        assert responses == []
