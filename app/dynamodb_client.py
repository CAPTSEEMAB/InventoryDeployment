import boto3
import uuid
import os
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

class DynamoDBClient:
    def __init__(self):
        self.dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        table_name = os.getenv('AWS_DYNAMODB_TABLE_NAME', 'inventory_products')
        self.inventory_products = self.dynamodb.Table(table_name)
    
    def _convert_decimals(self, obj):
        if isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_decimals(value) for key, value in obj.items()}
        elif isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return obj
    
    def _prepare_item(self, item: Dict) -> Dict:
        for key, value in item.items():
            if isinstance(value, float):
                item[key] = Decimal(str(value))
        return item
    
    def create_product(self, product_data: Dict) -> Dict:
        product_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        item = {
            'id': product_id,
            'created_at': timestamp,
            'updated_at': timestamp,
            **product_data
        }
        
        self.inventory_products.put_item(Item=self._prepare_item(item))
        return self._convert_decimals(item)
    
    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        response = self.inventory_products.get_item(Key={'id': product_id})
        return self._convert_decimals(response.get('Item')) if 'Item' in response else None
    
    def get_all_products(self, limit: int = 100) -> List[Dict]:
        response = self.inventory_products.scan(Limit=limit)
        return self._convert_decimals(response.get('Items', []))
    
    def update_product(self, product_id: str, updates: Dict) -> Optional[Dict]:
        updates['updated_at'] = datetime.now().isoformat()
        
        update_expr = "SET " + ", ".join([f"#{k} = :{k}" for k in updates.keys()])
        expr_attr_names = {f"#{k}": k for k in updates.keys()}
        expr_attr_values = {f":{k}": v for k, v in self._prepare_item(updates).items()}
        
        response = self.inventory_products.update_item(
            Key={'id': product_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values,
            ReturnValues='ALL_NEW'
        )
        return self._convert_decimals(response.get('Attributes'))
    
    def delete_product(self, product_id: str) -> bool:
        self.inventory_products.delete_item(Key={'id': product_id})
        return True

_client = None
def get_db_client():
    global _client
    if not _client:
        _client = DynamoDBClient()
    return _client
