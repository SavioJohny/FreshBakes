#!/usr/bin/env python3
"""
Quick script to create admin user - Edit the variables below and run.
"""

import boto3
from datetime import datetime
from werkzeug.security import generate_password_hash
import os

# ============ EDIT THESE VALUES ============
ADMIN_EMAIL = "admin@freshbakes.com"
ADMIN_PASSWORD = "admin123"  # Change this to a strong password!
ADMIN_NAME = "Admin User"
ADMIN_PHONE = "+1234567890"
# ===========================================

# AWS Configuration
REGION = os.environ.get('AWS_REGION', 'us-east-1')

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=REGION)
users_table = dynamodb.Table('FreshBakes_Users')

try:
    # Check if user exists
    response = users_table.get_item(Key={'email': ADMIN_EMAIL})
    
    if 'Item' in response:
        print(f"User {ADMIN_EMAIL} already exists. Updating to admin role...")
        users_table.update_item(
            Key={'email': ADMIN_EMAIL},
            UpdateExpression='SET #r = :r',
            ExpressionAttributeNames={'#r': 'role'},
            ExpressionAttributeValues={':r': 'admin'}
        )
        print(f"✅ User {ADMIN_EMAIL} updated to admin role!")
    else:
        # Create new admin user
        admin_user = {
            'email': ADMIN_EMAIL,
            'password_hash': generate_password_hash(ADMIN_PASSWORD),
            'name': ADMIN_NAME,
            'phone': ADMIN_PHONE,
            'role': 'admin',
            'is_active': True,
            'created_at': datetime.utcnow().isoformat()
        }
        
        users_table.put_item(Item=admin_user)
        print(f"✅ Admin user created successfully!")
        print(f"   Email: {ADMIN_EMAIL}")
        print(f"   Name: {ADMIN_NAME}")
        print(f"   Role: admin")
        
except Exception as e:
    print(f"❌ Error: {e}")
    raise
