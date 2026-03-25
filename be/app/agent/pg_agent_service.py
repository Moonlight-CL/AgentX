import uuid
import json
from datetime import datetime
from typing import Optional, List

from .agent import (
    AgentPO, AgentType, ModelProvider, AgentTool, AgentToolType, AgentRuntime,
    AgentPOService, ChatRecord, ChatResponse,
)
from ..utils.pg_config import get_pg_connection


class PGAgentPOService(AgentPOService):
    """PostgreSQL implementation of AgentPOService.

    Non-DB methods (build_strands_agent, build_strands_agent_with_session, stream_chat,
    agent_as_tool, get_all_available_tools) are inherited from AgentPOService.
    Only DynamoDB CRUD methods are overridden.
    """

    def __init__(self):
        # Do NOT call super().__init__() — that would init a DynamoDB resource
        pass

    def add_agent(self, agent_po: AgentPO, user_id: str = 'public'):
        if not isinstance(agent_po, AgentPO):
            raise TypeError("agent_po must be an instance of AgentPO")

        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agents (user_id, id, name, display_name, description, agent_type,
                        model_provider, model_id, sys_prompt, tools, envs, extras, shared_users,
                        shared_groups, is_public, creator, runtime)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb,
                            %s::jsonb, %s::jsonb, %s, %s, %s)
                    ON CONFLICT (user_id, id) DO UPDATE SET
                        name = EXCLUDED.name,
                        display_name = EXCLUDED.display_name,
                        description = EXCLUDED.description,
                        agent_type = EXCLUDED.agent_type,
                        model_provider = EXCLUDED.model_provider,
                        model_id = EXCLUDED.model_id,
                        sys_prompt = EXCLUDED.sys_prompt,
                        tools = EXCLUDED.tools,
                        envs = EXCLUDED.envs,
                        extras = EXCLUDED.extras,
                        shared_users = EXCLUDED.shared_users,
                        shared_groups = EXCLUDED.shared_groups,
                        is_public = EXCLUDED.is_public,
                        creator = EXCLUDED.creator,
                        runtime = EXCLUDED.runtime
                    """,
                    (
                        user_id, agent_po.id, agent_po.name, agent_po.display_name,
                        agent_po.description, agent_po.agent_type.value,
                        agent_po.model_provider.value, agent_po.model_id,
                        agent_po.sys_prompt,
                        json.dumps([t.model_dump_json() for t in agent_po.tools]),
                        agent_po.envs,
                        json.dumps(agent_po.extras) if agent_po.extras else None,
                        json.dumps(agent_po.shared_users or []),
                        json.dumps(agent_po.shared_groups or []),
                        agent_po.is_public,
                        user_id,
                        agent_po.runtime.value,
                    ),
                )

    def get_agent(self, user_id: str, id: str) -> Optional[AgentPO]:
        keys = [user_id, 'public']
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                for k in keys:
                    cur.execute(
                        "SELECT * FROM agents WHERE user_id = %s AND id = %s",
                        (k, id),
                    )
                    row = cur.fetchone()
                    if row:
                        col_names = [desc[0] for desc in cur.description]
                        return self._map_pg_agent(dict(zip(col_names, row)))
        return None

    def list_agents(self, user_id: str, user_groups: Optional[List[str]] = None) -> List[AgentPO]:
        user_groups = user_groups or []
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT * FROM agents
                        WHERE user_id = %s OR user_id = 'public' OR is_public = TRUE
                           OR shared_users @> %s::jsonb
                           OR (%s::text[] IS NOT NULL AND shared_groups ?| %s::text[])
                        """,
                        (
                            user_id,
                            json.dumps([user_id]),
                            user_groups if user_groups else None,
                            user_groups if user_groups else None,
                        ),
                    )
                    rows = cur.fetchall()
                    col_names = [desc[0] for desc in cur.description]
                    agents = [self._map_pg_agent(dict(zip(col_names, row))) for row in rows]
                    return sorted(agents, key=lambda a: (a.name or "").lower())
        except Exception as e:
            print(f"Error listing agents: {e}")
            return []

    def delete_agent(self, user_id: str, id: str) -> bool:
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM agents WHERE user_id = %s AND id = %s",
                        (user_id, id),
                    )
            return True
        except Exception as e:
            print(f"Error deleting agent {id}: {e}")
            return False

    def update_agent_sharing(
        self, user_id: str, agent_id: str,
        shared_users: Optional[List[str]] = None,
        shared_groups: Optional[List[str]] = None,
        is_public: Optional[bool] = None,
    ):
        agent = self.get_agent(user_id, agent_id)
        if not agent:
            return False, "Agent not found or you don't have permission to share it"

        fields = []
        values = []
        if shared_users is not None:
            fields.append('shared_users = %s::jsonb')
            values.append(json.dumps(shared_users))
        if shared_groups is not None:
            fields.append('shared_groups = %s::jsonb')
            values.append(json.dumps(shared_groups))
        if is_public is not None:
            fields.append('is_public = %s')
            values.append(is_public)

        if not fields:
            return True, ""

        values.extend([user_id, agent_id])
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"UPDATE agents SET {', '.join(fields)} WHERE user_id = %s AND id = %s",
                        values,
                    )
            return True, ""
        except Exception as e:
            return False, str(e)

    def make_agent_public(self, agent_id: str) -> bool:
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE agents SET is_public = TRUE WHERE id = %s",
                        (agent_id,),
                    )
            return True
        except Exception as e:
            print(f"Error making agent {agent_id} public: {e}")
            return False

    def get_agent_sharing_info(self, user_id: str, agent_id: str):
        agent = self.get_agent(user_id, agent_id)
        if not agent:
            return None, "Agent not found or you don't have permission to view its sharing settings"
        sharing_info = {
            "agent_id": agent.id,
            "shared_users": agent.shared_users or [],
            "shared_groups": agent.shared_groups or [],
            "is_public": agent.is_public,
        }
        return sharing_info, ""

    def _map_pg_agent(self, item: dict) -> AgentPO:
        tools_raw = item.get('tools', '[]')
        if isinstance(tools_raw, str):
            tools_list = json.loads(tools_raw)
        else:
            tools_list = tools_raw or []

        def json_to_agent_tool(tool_json) -> AgentTool:
            if isinstance(tool_json, str):
                tool_json = json.loads(tool_json)
            return AgentTool(
                name=tool_json['name'],
                display_name=tool_json.get('display_name', tool_json['name']),
                category=tool_json['category'],
                desc=tool_json['desc'],
                type=AgentToolType(tool_json['type']),
                mcp_server_url=tool_json.get('mcp_server_url'),
                mcp_server_headers=tool_json.get('mcp_server_headers'),
                agent_id=tool_json.get('agent_id'),
            )

        def _to_int(val, default=1, valid=(1, 2)):
            if isinstance(val, (int, float)):
                val = int(val)
            elif isinstance(val, str):
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    val = default
            return val if val in valid else default

        agent_type_value = _to_int(item['agent_type'])

        model_provider_value = item['model_provider']
        if isinstance(model_provider_value, str):
            try:
                model_provider_value = int(model_provider_value)
            except (ValueError, TypeError):
                pass

        runtime_value = _to_int(item.get('runtime', 1))

        extras = item.get('extras')
        if isinstance(extras, str):
            extras = json.loads(extras)

        shared_users = item.get('shared_users', [])
        if isinstance(shared_users, str):
            shared_users = json.loads(shared_users)

        shared_groups = item.get('shared_groups', [])
        if isinstance(shared_groups, str):
            shared_groups = json.loads(shared_groups)

        return AgentPO(
            id=item['id'],
            name=item['name'],
            display_name=item['display_name'],
            description=item['description'],
            agent_type=AgentType(agent_type_value),
            model_provider=ModelProvider(model_provider_value),
            model_id=item['model_id'],
            sys_prompt=item['sys_prompt'],
            tools=[json_to_agent_tool(t) for t in tools_list],
            envs=item.get('envs', ''),
            extras=extras,
            shared_users=shared_users or None,
            shared_groups=shared_groups or None,
            is_public=item.get('is_public', False),
            creator=item.get('creator') or item.get('user_id'),
            runtime=AgentRuntime(runtime_value),
        )


class PGChatRecordService:
    """PostgreSQL implementation of ChatRecordService."""

    def __init__(self):
        from .pg_session_repository import PostgreSQLSessionRepository
        self.session_repository = PostgreSQLSessionRepository()

    def add_chat_record(self, record: ChatRecord):
        if not record.id:
            record.id = uuid.uuid4().hex

        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chat_records (user_id, id, agent_id, user_message, create_time,
                        record_type, config, status, end_time, results, error)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (user_id, id) DO UPDATE SET
                        agent_id = EXCLUDED.agent_id,
                        user_message = EXCLUDED.user_message,
                        record_type = EXCLUDED.record_type,
                        config = EXCLUDED.config,
                        status = EXCLUDED.status,
                        end_time = EXCLUDED.end_time,
                        results = EXCLUDED.results,
                        error = EXCLUDED.error
                    """,
                    (
                        record.user_id, record.id, record.agent_id,
                        record.user_message, record.create_time,
                        record.record_type,
                        json.dumps(record.config) if record.config is not None else None,
                        record.status, record.end_time,
                        json.dumps(record.results) if record.results is not None else None,
                        record.error,
                    ),
                )

    def get_chat_record(self, user_id: str, id: str) -> Optional[ChatRecord]:
        keys = [user_id, 'public']
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                for k in keys:
                    cur.execute(
                        "SELECT * FROM chat_records WHERE user_id = %s AND id = %s",
                        (k, id),
                    )
                    row = cur.fetchone()
                    if row:
                        col_names = [desc[0] for desc in cur.description]
                        return self._row_to_record(dict(zip(col_names, row)))
        return None

    def get_chat_records_by_user(self, user_id: str, record_type: Optional[str] = None) -> List[ChatRecord]:
        keys = [user_id, 'public']
        records = []
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                for k in keys:
                    if record_type:
                        cur.execute(
                            "SELECT * FROM chat_records WHERE user_id = %s AND record_type = %s LIMIT 100",
                            (k, record_type),
                        )
                    else:
                        cur.execute(
                            "SELECT * FROM chat_records WHERE user_id = %s LIMIT 100",
                            (k,),
                        )
                    rows = cur.fetchall()
                    col_names = [desc[0] for desc in cur.description]
                    records.extend([self._row_to_record(dict(zip(col_names, row))) for row in rows])
        return sorted(records, key=lambda x: x.create_time, reverse=True)

    def get_records_by_agent_id(
        self, user_id: str, agent_id: str, record_type: Optional[str] = None
    ) -> List[ChatRecord]:
        keys = [user_id, 'public']
        records = []
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                for k in keys:
                    if record_type:
                        cur.execute(
                            "SELECT * FROM chat_records WHERE user_id = %s AND agent_id = %s AND record_type = %s LIMIT 100",
                            (k, agent_id, record_type),
                        )
                    else:
                        cur.execute(
                            "SELECT * FROM chat_records WHERE user_id = %s AND agent_id = %s LIMIT 100",
                            (k, agent_id),
                        )
                    rows = cur.fetchall()
                    col_names = [desc[0] for desc in cur.description]
                    records.extend([self._row_to_record(dict(zip(col_names, row))) for row in rows])
        return sorted(records, key=lambda x: x.create_time, reverse=True)

    def add_chat_response(self, response: ChatResponse):
        # Deprecated — sessions handle message storage
        pass

    def get_all_chat_responses(self, chat_id: str) -> List[ChatResponse]:
        return []

    def get_all_chat_responses_from_session(self, chat_id: str, agent_id: str) -> List[ChatResponse]:
        try:
            session_agent_id = f"{agent_id}_{chat_id}"
            session_messages = self.session_repository.list_messages(
                session_id=chat_id, agent_id=session_agent_id, read_attachment=False
            )
            chat_responses = []
            for i, session_message in enumerate(session_messages):
                message_dict = session_message.to_dict()
                chat_resp = ChatResponse(
                    chat_id=chat_id,
                    resp_no=i,
                    content=json.dumps(message_dict),
                    create_time=session_message.created_at or datetime.now().isoformat(),
                )
                chat_responses.append(chat_resp)
            return chat_responses
        except Exception as e:
            print(f"Error getting chat responses from session: {e}")
            return []

    def del_chat(self, user_id: str, id: str):
        """Delete a chat record and its associated session data."""
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM chat_records WHERE user_id = %s AND id = %s",
                        (user_id, id),
                    )
                    # Clean up session messages
                    cur.execute(
                        "DELETE FROM session_messages WHERE session_id = %s",
                        (id,),
                    )
                    # Clean up session agents
                    cur.execute(
                        "DELETE FROM session_agents WHERE session_id = %s",
                        (id,),
                    )
                    # Clean up session itself
                    cur.execute(
                        "DELETE FROM chat_sessions WHERE session_id = %s",
                        (id,),
                    )
        except Exception as e:
            print(f"Error deleting chat {id}: {e}")

    def _row_to_record(self, item: dict) -> ChatRecord:
        config = item.get('config')
        if isinstance(config, str):
            config = json.loads(config)
        results = item.get('results')
        if isinstance(results, str):
            results = json.loads(results)
        return ChatRecord(
            id=item['id'],
            agent_id=item['agent_id'],
            user_id=item.get('user_id', ''),
            user_message=item['user_message'],
            create_time=item['create_time'],
            record_type=item.get('record_type', 'agent'),
            config=config,
            status=item.get('status'),
            end_time=item.get('end_time'),
            results=results,
            error=item.get('error'),
        )
