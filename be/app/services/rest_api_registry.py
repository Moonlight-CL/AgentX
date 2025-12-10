from typing import Dict, List, Optional
import boto3
from boto3.dynamodb.conditions import Key
from app.utils.aws_config import get_rest_api_registry_table


class RestAPIRegistry:
    def __init__(self):
        # self.dynamodb = boto3.resource('dynamodb')
        # self.table = self.dynamodb.Table(table_name)
        self.table = get_rest_api_registry_table()
    
    async def get_user_apis(self, user_id: str) -> List[Dict]:
        """Get all REST APIs registered by a user"""
        response = self.table.query(
            KeyConditionExpression=Key('user_id').eq(user_id)
        )
        return response.get('Items', [])
    
    async def get_api(self, user_id: str, api_id: str) -> Optional[Dict]:
        """Get a specific REST API"""
        response = self.table.get_item(
            Key={'user_id': user_id, 'api_id': api_id}
        )
        return response.get('Item')
    
    async def create_api(self, user_id: str, api_id: str, config: Dict) -> Dict:
        """Create a new REST API registration"""
        item = {
            'user_id': user_id,
            'api_id': api_id,
            **config
        }
        self.table.put_item(Item=item)
        return item
    
    async def update_api(self, user_id: str, api_id: str, config: Dict) -> Dict:
        """Update an existing REST API"""
        item = {
            'user_id': user_id,
            'api_id': api_id,
            **config
        }
        self.table.put_item(Item=item)
        return item
    
    async def delete_api(self, user_id: str, api_id: str):
        """Delete a REST API registration"""
        self.table.delete_item(
            Key={'user_id': user_id, 'api_id': api_id}
        )
