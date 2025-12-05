#!/usr/bin/env python3
"""
Script to create the RestAPIRegistry DynamoDB table.
"""
import boto3

def create_rest_api_registry_table():
    dynamodb = boto3.resource('dynamodb')
    
    table_name = 'RestAPIRegistry'
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'api_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'api_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        print(f"Creating table {table_name}...")
        table.wait_until_exists()
        print(f"Table {table_name} created successfully!")
        
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        print(f"Table {table_name} already exists.")

if __name__ == '__main__':
    create_rest_api_registry_table()
