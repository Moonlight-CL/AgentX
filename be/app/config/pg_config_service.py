import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from .models import SystemConfig, ConfigCategory, CreateConfigRequest, UpdateConfigRequest
from ..utils.pg_config import get_pg_connection


class PGConfigService:
    """PostgreSQL implementation of ConfigService. No Decimal conversion needed."""

    def create_config(self, config_request: CreateConfigRequest) -> SystemConfig:
        current_time = datetime.now().isoformat()
        config_data = {
            **config_request.model_dump(),
            'created_at': current_time,
            'updated_at': current_time,
        }
        config = SystemConfig(**config_data)

        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO configurations (key, value, key_display_name, type, parent, seq_num,
                                                created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (key) DO UPDATE SET
                        value = EXCLUDED.value,
                        key_display_name = EXCLUDED.key_display_name,
                        type = EXCLUDED.type,
                        parent = EXCLUDED.parent,
                        seq_num = EXCLUDED.seq_num,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (
                        config.key, config.value, config.key_display_name,
                        config.type, config.parent, config.seq_num,
                        config.created_at, config.updated_at,
                    ),
                )
        return config

    def get_config(self, key: str) -> Optional[SystemConfig]:
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM configurations WHERE key = %s", (key,))
                    row = cur.fetchone()
                    if row:
                        col_names = [desc[0] for desc in cur.description]
                        return SystemConfig(**dict(zip(col_names, row)))
            return None
        except Exception as e:
            print(f"Error getting config: {e}")
            return None

    def update_config(self, key: str, update_request: UpdateConfigRequest) -> Optional[SystemConfig]:
        try:
            existing = self.get_config(key)
            if not existing:
                return None

            update_data = update_request.model_dump(exclude_unset=True)
            updated_data = {
                **existing.model_dump(),
                **update_data,
                'updated_at': datetime.now().isoformat(),
            }
            config = SystemConfig(**updated_data)

            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE configurations SET value = %s, key_display_name = %s, type = %s,
                            parent = %s, seq_num = %s, updated_at = %s
                        WHERE key = %s
                        """,
                        (
                            config.value, config.key_display_name, config.type,
                            config.parent, config.seq_num, config.updated_at, key,
                        ),
                    )
            return config
        except Exception as e:
            print(f"Error updating config: {e}")
            return None

    def delete_config(self, key: str) -> bool:
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM configurations WHERE key = %s", (key,))
            return True
        except Exception as e:
            print(f"Error deleting config: {e}")
            return False

    def list_configs_by_parent(self, parent: str) -> List[SystemConfig]:
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM configurations WHERE parent = %s ORDER BY seq_num",
                        (parent,),
                    )
                    rows = cur.fetchall()
                    col_names = [desc[0] for desc in cur.description]
                    return [SystemConfig(**dict(zip(col_names, row))) for row in rows]
        except Exception as e:
            print(f"Error listing configs by parent: {e}")
            return []

    def list_all_configs(self) -> List[SystemConfig]:
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM configurations ORDER BY COALESCE(parent, ''), seq_num"
                    )
                    rows = cur.fetchall()
                    col_names = [desc[0] for desc in cur.description]
                    return [SystemConfig(**dict(zip(col_names, row))) for row in rows]
        except Exception as e:
            print(f"Error listing all configs: {e}")
            return []

    def get_category_tree(self) -> List[ConfigCategory]:
        try:
            all_configs = self.list_all_configs()
            categories = [c for c in all_configs if c.type == 'category']
            items = [c for c in all_configs if c.type == 'item']

            root_categories = []
            category_map = {}

            for cat in categories:
                cat_obj = ConfigCategory(
                    key=cat.key,
                    key_display_name=cat.key_display_name,
                    parent=cat.parent,
                    configs=[],
                )
                category_map[cat.key] = cat_obj
                if not cat.parent:
                    root_categories.append(cat_obj)

            for cat in categories:
                if cat.parent and cat.parent in category_map:
                    category_map[cat.parent].children.append(category_map[cat.key])

            for item in items:
                if item.parent and item.parent in category_map:
                    category_map[item.parent].configs.append(item)

            return root_categories
        except Exception as e:
            print(f"Error getting category tree: {e}")
            return []

    def get_root_categories(self) -> List[SystemConfig]:
        try:
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM configurations WHERE type = 'category' AND parent IS NULL ORDER BY seq_num"
                    )
                    rows = cur.fetchall()
                    col_names = [desc[0] for desc in cur.description]
                    return [SystemConfig(**dict(zip(col_names, row))) for row in rows]
        except Exception as e:
            print(f"Error getting root categories: {e}")
            return []

    def create_model_provider_category(self, provider_key: str, provider_display_name: str) -> SystemConfig:
        config_request = CreateConfigRequest(
            key=f"model_providers.{provider_key}",
            value="{}",
            key_display_name=provider_display_name,
            type="category",
            parent="model_providers",
            seq_num=0,
        )
        return self.create_config(config_request)

    def create_model_provider_config(self, provider_key: str, config_key: str, config_data: Dict[str, Any]) -> SystemConfig:
        config_request = CreateConfigRequest(
            key=f"model_providers.{provider_key}.{config_key}",
            value=json.dumps(config_data),
            key_display_name=config_key,
            type="item",
            parent=f"{provider_key}",
            seq_num=0,
        )
        return self.create_config(config_request)
