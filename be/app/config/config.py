import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal
from botocore.exceptions import ClientError
from ..utils.aws_config import get_config_table
from .models import SystemConfig, ConfigCategory, CreateConfigRequest, UpdateConfigRequest

def convert_floats_to_decimal(obj):
    """
    Recursively convert float values to Decimal for DynamoDB compatibility.
    
    Args:
        obj: The object to convert (dict, list, or primitive)
        
    Returns:
        The object with floats converted to Decimal
    """
    if isinstance(obj, dict):
        return {key: convert_floats_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj

def convert_decimals_to_float(obj):
    """
    Recursively convert Decimal values back to float for frontend compatibility.
    
    Args:
        obj: The object to convert (dict, list, or primitive)
        
    Returns:
        The object with Decimals converted to float
    """
    if isinstance(obj, dict):
        return {key: convert_decimals_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_float(item) for item in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj

class ConfigService:
    """Service class for system configuration management."""
    
    def __init__(self):
        self.config_table = get_config_table()
    
    def create_config(self, config_request: CreateConfigRequest) -> SystemConfig:
        """
        Create a new system configuration.
        
        Args:
            config_request: The configuration creation request
            
        Returns:
            SystemConfig: The created configuration
        """
        current_time = datetime.now().isoformat()
        
        config_data = {
            **config_request.model_dump(),
            'created_at': current_time,
            'updated_at': current_time
        }
        
        config = SystemConfig(**config_data)
        
        # Convert floats to Decimal for DynamoDB compatibility
        config_data_for_db = convert_floats_to_decimal(config.model_dump())
        
        # Save to DynamoDB - using key as both partition key and sort key
        self.config_table.put_item(Item=config_data_for_db)
        
        return config
    
    def get_config(self, key: str) -> Optional[SystemConfig]:
        """
        Get a configuration by key.
        
        Args:
            key: The configuration key
            
        Returns:
            SystemConfig or None: The configuration if found
        """
        try:
            response = self.config_table.get_item(
                Key={'key': key}
            )
            
            if 'Item' not in response:
                return None
            
            item = response['Item']
            
            # Convert Decimals back to floats for frontend compatibility
            item_with_floats = convert_decimals_to_float(item)
            
            return SystemConfig(**item_with_floats)
        except ClientError as e:
            print(f"Error getting config: {e}")
            return None
    
    def update_config(self, key: str, update_request: UpdateConfigRequest) -> Optional[SystemConfig]:
        """
        Update an existing configuration.
        
        Args:
            key: The configuration key
            update_request: The configuration update request
            
        Returns:
            SystemConfig or None: The updated configuration if successful
        """
        try:
            # First, get the existing configuration
            existing_config = self.get_config(key)
            if not existing_config:
                return None
            
            # Update the configuration
            update_data = update_request.model_dump(exclude_unset=True)
            updated_data = {
                **existing_config.model_dump(),
                **update_data,
                'updated_at': datetime.now().isoformat()
            }
            
            config = SystemConfig(**updated_data)
            
            # Convert floats to Decimal for DynamoDB compatibility
            config_data_for_db = convert_floats_to_decimal(config.model_dump())
            
            # Save to DynamoDB
            self.config_table.put_item(Item=config_data_for_db)
            
            return config
        except ClientError as e:
            print(f"Error updating config: {e}")
            return None
    
    def delete_config(self, key: str) -> bool:
        """
        Delete a configuration.
        
        Args:
            key: The configuration key
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            self.config_table.delete_item(
                Key={'key': key}
            )
            return True
        except ClientError as e:
            print(f"Error deleting config: {e}")
            return False
    
    def list_configs_by_parent(self, parent: str) -> List[SystemConfig]:
        """
        List all configurations under a specific parent.
        
        Args:
            parent: The parent category key
            
        Returns:
            List[SystemConfig]: List of configurations under the parent
        """
        try:
            response = self.config_table.scan(
                FilterExpression='parent = :parent',
                ExpressionAttributeValues={':parent': parent}
            )
            
            configs = []
            for item in response.get('Items', []):
                # Convert Decimals back to floats for frontend compatibility
                item_with_floats = convert_decimals_to_float(item)
                configs.append(SystemConfig(**item_with_floats))
            
            # Sort by seq_num
            configs.sort(key=lambda x: x.seq_num)
            
            return configs
        except ClientError as e:
            print(f"Error listing configs by parent: {e}")
            return []
    
    def list_all_configs(self) -> List[SystemConfig]:
        """
        List all configurations.
        
        Returns:
            List[SystemConfig]: List of all configurations
        """
        try:
            response = self.config_table.scan()
            
            configs = []
            for item in response.get('Items', []):
                # Convert Decimals back to floats for frontend compatibility
                item_with_floats = convert_decimals_to_float(item)
                configs.append(SystemConfig(**item_with_floats))
            
            # Sort by parent and seq_num
            configs.sort(key=lambda x: (x.parent or '', x.seq_num))
            
            return configs
        except ClientError as e:
            print(f"Error listing all configs: {e}")
            return []
    
    def get_category_tree(self) -> List[ConfigCategory]:
        """
        Get the configuration category tree structure.
        
        Returns:
            List[ConfigCategory]: List of root categories with their children and configs
        """
        try:
            # Get all configurations
            all_configs = self.list_all_configs()
            
            # Separate categories and items
            categories = [config for config in all_configs if config.type == 'category']
            items = [config for config in all_configs if config.type == 'item']
            
            # Build category tree
            root_categories = []
            category_map = {}
            
            # First pass: create all category objects
            for category_config in categories:
                category_obj = ConfigCategory(
                    key=category_config.key,
                    key_display_name=category_config.key_display_name,
                    parent=category_config.parent,
                    configs=[]
                )
                category_map[category_config.key] = category_obj
                
                # If it's a root category (no parent), add to root list
                if not category_config.parent:
                    root_categories.append(category_obj)
            
            # Second pass: build parent-child relationships
            for category_config in categories:
                if category_config.parent and category_config.parent in category_map:
                    parent = category_map[category_config.parent]
                    child = category_map[category_config.key]
                    parent.children.append(child)
            
            # Third pass: assign items to their parent categories
            for item in items:
                if item.parent and item.parent in category_map:
                    parent_category = category_map[item.parent]
                    parent_category.configs.append(item)
            
            return root_categories
        except Exception as e:
            print(f"Error getting category tree: {e}")
            return []
    
    def get_root_categories(self) -> List[SystemConfig]:
        """
        Get all root categories (categories with no parent).
        
        Returns:
            List[SystemConfig]: List of root categories
        """
        try:
            response = self.config_table.scan(
                FilterExpression='#type = :type AND attribute_not_exists(parent)',
                ExpressionAttributeNames={'#type': 'type'},
                ExpressionAttributeValues={':type': 'category'}
            )
            
            categories = []
            for item in response.get('Items', []):
                # Convert Decimals back to floats for frontend compatibility
                item_with_floats = convert_decimals_to_float(item)
                categories.append(SystemConfig(**item_with_floats))
            
            # Sort by seq_num
            categories.sort(key=lambda x: x.seq_num)
            
            return categories
        except ClientError as e:
            print(f"Error getting root categories: {e}")
            return []
    
    def create_model_provider_category(self, provider_key: str, provider_display_name: str) -> SystemConfig:
        """
        Create a model provider category under model_providers.
        
        Args:
            provider_key: The provider key (e.g., "bedrock", "openai")
            provider_display_name: The provider display name
            
        Returns:
            SystemConfig: The created category
        """
        config_request = CreateConfigRequest(
            key=f"model_providers.{provider_key}",
            value="{}",  # Empty JSON object for categories
            key_display_name=provider_display_name,
            type="category",
            parent="model_providers",
            seq_num=0
        )
        
        return self.create_config(config_request)
    
    def create_model_provider_config(self, provider_key: str, config_key: str, config_data: Dict[str, Any]) -> SystemConfig:
        """
        Create a model provider configuration item.
        
        Args:
            provider_key: The provider key (e.g., "bedrock", "openai")
            config_key: The configuration key
            config_data: The configuration data
            
        Returns:
            SystemConfig: The created configuration
        """
        config_request = CreateConfigRequest(
            key=f"model_providers.{provider_key}.{config_key}",
            value=json.dumps(config_data),
            key_display_name=config_key,
            type="item",
            parent=f"{provider_key}",
            seq_num=0
        )
        
        return self.create_config(config_request)
