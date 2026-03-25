import uuid
import json
from typing import List, Optional

from .mcp import HttpMCPServer
from ..utils.pg_config import get_pg_connection


class PGMCPService:
    """PostgreSQL implementation of MCPService."""

    def add_mcp_server(self, server: HttpMCPServer, user_id: str = 'public'):
        if not server.id:
            server.id = uuid.uuid4().hex

        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO http_mcp_servers (user_id, id, name, "desc", host, headers,
                                                  client_id, client_secret, token_url, scope)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
                    ON CONFLICT (user_id, id) DO UPDATE SET
                        name = EXCLUDED.name,
                        "desc" = EXCLUDED."desc",
                        host = EXCLUDED.host,
                        headers = EXCLUDED.headers,
                        client_id = EXCLUDED.client_id,
                        client_secret = EXCLUDED.client_secret,
                        token_url = EXCLUDED.token_url,
                        scope = EXCLUDED.scope
                    """,
                    (
                        user_id, server.id, server.name, server.desc, server.host,
                        json.dumps(server.headers) if server.headers else None,
                        server.client_id, server.client_secret, server.token_url, server.scope,
                    ),
                )

    def list_mcp_servers(self, user_id: str) -> List[HttpMCPServer]:
        keys = [user_id, 'public']
        items = []
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                for k in keys:
                    cur.execute(
                        "SELECT * FROM http_mcp_servers WHERE user_id = %s LIMIT 100",
                        (k,),
                    )
                    rows = cur.fetchall()
                    col_names = [desc[0] for desc in cur.description]
                    for row in rows:
                        items.append(dict(zip(col_names, row)))
        return [self._row_to_server(item) for item in items]

    def get_mcp_server(self, user_id: str, id: str) -> Optional[HttpMCPServer]:
        keys = [user_id, 'public']
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                for k in keys:
                    cur.execute(
                        "SELECT * FROM http_mcp_servers WHERE user_id = %s AND id = %s",
                        (k, id),
                    )
                    row = cur.fetchone()
                    if row:
                        col_names = [desc[0] for desc in cur.description]
                        return self._row_to_server(dict(zip(col_names, row)))
        return None

    def delete_mcp_server(self, user_id: str, id: str) -> bool:
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM http_mcp_servers WHERE user_id = %s AND id = %s",
                        (user_id, id),
                    )
            return True
        except Exception as e:
            print(f"Error deleting MCP server {id}: {e}")
            return False

    def _row_to_server(self, item: dict) -> HttpMCPServer:
        headers = item.get('headers')
        if isinstance(headers, str):
            import json as _json
            headers = _json.loads(headers)
        return HttpMCPServer(
            id=item['id'],
            name=item['name'],
            desc=item['desc'],
            host=item['host'],
            headers=headers,
            client_id=item.get('client_id'),
            client_secret=item.get('client_secret'),
            token_url=item.get('token_url'),
            scope=item.get('scope'),
        )
