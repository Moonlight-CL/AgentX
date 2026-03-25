"""
Integration tests for PGAgentPOService against a real PostgreSQL database.

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


def _make_agent(**overrides):
    """Create an AgentPO with sensible defaults, allowing field overrides."""
    from app.agent.agent import AgentPO, AgentType, ModelProvider, AgentRuntime

    defaults = dict(
        id=uuid.uuid4().hex,
        name='Test Agent',
        display_name='Test',
        description='Integration test agent',
        agent_type=AgentType.plain,
        model_provider=ModelProvider.bedrock,
        model_id='anthropic.claude-3-sonnet-20240229-v1:0',
        sys_prompt='You are a helpful assistant.',
        tools=[],
        envs='',
        is_public=False,
    )
    defaults.update(overrides)
    return AgentPO(**defaults)


# ---------------------------------------------------------------------------
# add_agent / get_agent
# ---------------------------------------------------------------------------

def test_add_and_get_agent(agent_service):
    user_id = _uid('user')
    agent = _make_agent()
    agent_service.add_agent(agent, user_id=user_id)

    fetched = agent_service.get_agent(user_id, agent.id)
    assert fetched is not None
    assert fetched.id == agent.id
    assert fetched.name == agent.name
    assert fetched.description == agent.description


def test_get_agent_not_found(agent_service):
    result = agent_service.get_agent(_uid('user'), uuid.uuid4().hex)
    assert result is None


def test_get_agent_from_public(agent_service):
    """An agent added under 'public' is retrievable by any user_id."""
    agent = _make_agent()
    agent_service.add_agent(agent, user_id='public')

    other_user = _uid('user')
    fetched = agent_service.get_agent(other_user, agent.id)
    assert fetched is not None
    assert fetched.id == agent.id


# ---------------------------------------------------------------------------
# list_agents
# ---------------------------------------------------------------------------

def test_list_agents_own_and_public(agent_service):
    user_id = _uid('user')
    own_agent = _make_agent(name='Own Agent')
    public_agent = _make_agent(name='Public Agent')

    agent_service.add_agent(own_agent, user_id=user_id)
    agent_service.add_agent(public_agent, user_id='public')

    agents = agent_service.list_agents(user_id)
    ids = {a.id for a in agents}
    assert own_agent.id in ids
    assert public_agent.id in ids


def test_list_agents_shared_with_user(agent_service):
    owner_id = _uid('owner')
    target_user = _uid('target')
    shared_agent = _make_agent(name='Shared Agent', shared_users=[target_user])

    agent_service.add_agent(shared_agent, user_id=owner_id)

    agents = agent_service.list_agents(target_user)
    ids = {a.id for a in agents}
    assert shared_agent.id in ids


def test_list_agents_shared_with_group(agent_service):
    owner_id = _uid('owner')
    group_name = 'grp_' + uuid.uuid4().hex[:6]
    grp_agent = _make_agent(name='Group Agent', shared_groups=[group_name])

    agent_service.add_agent(grp_agent, user_id=owner_id)

    # A user who is a member of that group can see the agent
    agents = agent_service.list_agents(_uid('any_user'), user_groups=[group_name])
    ids = {a.id for a in agents}
    assert grp_agent.id in ids


def test_list_agents_public_is_visible(agent_service):
    """An agent with is_public=True under any user is visible to everyone."""
    other_user = _uid('other')
    pub_agent = _make_agent(name='IsPublic Agent', is_public=True)
    agent_service.add_agent(pub_agent, user_id=other_user)

    listing_user = _uid('listing')
    agents = agent_service.list_agents(listing_user)
    ids = {a.id for a in agents}
    assert pub_agent.id in ids


# ---------------------------------------------------------------------------
# delete_agent
# ---------------------------------------------------------------------------

def test_delete_agent(agent_service):
    user_id = _uid('user')
    agent = _make_agent()
    agent_service.add_agent(agent, user_id=user_id)

    result = agent_service.delete_agent(user_id, agent.id)
    assert result is True

    assert agent_service.get_agent(user_id, agent.id) is None


# ---------------------------------------------------------------------------
# update_agent_sharing / get_agent_sharing_info
# ---------------------------------------------------------------------------

def test_update_agent_sharing(agent_service):
    user_id = _uid('user')
    agent = _make_agent()
    agent_service.add_agent(agent, user_id=user_id)

    new_shared_users = [_uid('shareduser')]
    new_shared_groups = ['group_a']
    ok, err = agent_service.update_agent_sharing(
        user_id, agent.id,
        shared_users=new_shared_users,
        shared_groups=new_shared_groups,
        is_public=False,
    )
    assert ok is True
    assert err == ''

    sharing_info, err = agent_service.get_agent_sharing_info(user_id, agent.id)
    assert err == ''
    assert sharing_info['shared_users'] == new_shared_users
    assert sharing_info['shared_groups'] == new_shared_groups


# ---------------------------------------------------------------------------
# make_agent_public
# ---------------------------------------------------------------------------

def test_make_agent_public(agent_service):
    user_id = _uid('user')
    agent = _make_agent(is_public=False)
    agent_service.add_agent(agent, user_id=user_id)

    result = agent_service.make_agent_public(agent.id)
    assert result is True

    fetched = agent_service.get_agent(user_id, agent.id)
    assert fetched.is_public is True


# ---------------------------------------------------------------------------
# add_agent upsert behaviour
# ---------------------------------------------------------------------------

def test_add_agent_upsert(agent_service):
    """Calling add_agent twice with the same (user_id, id) updates the record."""
    user_id = _uid('user')
    agent_id = uuid.uuid4().hex

    first = _make_agent(id=agent_id, name='First Name')
    agent_service.add_agent(first, user_id=user_id)

    second = _make_agent(id=agent_id, name='Updated Name')
    agent_service.add_agent(second, user_id=user_id)

    fetched = agent_service.get_agent(user_id, agent_id)
    assert fetched is not None
    assert fetched.name == 'Updated Name'
