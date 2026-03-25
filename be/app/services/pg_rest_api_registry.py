import json
from typing import Dict, List, Optional

from ..utils.pg_config import get_pg_connection


class PGRestAPIRegistry:
    """PostgreSQL implementation of RestAPIRegistry."""

    async def get_user_apis(self, user_id: str) -> List[Dict]:
        return self.get_user_apis_sync(user_id)

    def get_user_apis_sync(self, user_id: str) -> List[Dict]:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM rest_api_registry WHERE user_id = %s",
                    (user_id,),
                )
                rows = cur.fetchall()
                col_names = [desc[0] for desc in cur.description]
                return [self._row_to_dict(dict(zip(col_names, row))) for row in rows]

    async def get_api(self, user_id: str, api_id: str) -> Optional[Dict]:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM rest_api_registry WHERE user_id = %s AND api_id = %s",
                    (user_id, api_id),
                )
                row = cur.fetchone()
                if row:
                    col_names = [desc[0] for desc in cur.description]
                    return self._row_to_dict(dict(zip(col_names, row)))
        return None

    async def create_api(self, user_id: str, api_id: str, config: Dict) -> Dict:
        endpoints = config.get('endpoints', [])
        name = config.get('name', '')
        from datetime import datetime
        current_time = datetime.now().isoformat()

        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO rest_api_registry (user_id, api_id, name, endpoints, created_at, updated_at)
                    VALUES (%s, %s, %s, %s::jsonb, %s, %s)
                    ON CONFLICT (user_id, api_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        endpoints = EXCLUDED.endpoints,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (user_id, api_id, name, json.dumps(endpoints), current_time, current_time),
                )
        item = {'user_id': user_id, 'api_id': api_id, **config}
        return item

    async def update_api(self, user_id: str, api_id: str, config: Dict) -> Dict:
        return await self.create_api(user_id, api_id, config)

    async def delete_api(self, user_id: str, api_id: str):
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM rest_api_registry WHERE user_id = %s AND api_id = %s",
                    (user_id, api_id),
                )

    def _row_to_dict(self, item: dict) -> dict:
        endpoints = item.get('endpoints')
        if isinstance(endpoints, str):
            endpoints = json.loads(endpoints)
        return {
            'user_id': item['user_id'],
            'api_id': item['api_id'],
            'name': item.get('name', ''),
            'endpoints': endpoints or [],
            'created_at': item.get('created_at'),
            'updated_at': item.get('updated_at'),
        }
