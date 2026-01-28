#!/usr/bin/env python3
"""
Script to create an admin user in DynamoDB for FreshBakes AWS deployment.
Run this script on your EC2 instance or locally with AWS credentials configured.
"""

import boto3
from datetime import datetime
from werkzeug.security import generate_password_hash
import os

# AWS Configuration
REGION = os.environ.get('AWS_REGION', 'us-east-1')

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=REGION)
users_table = dynamodb.Table('FreshBakes_Users')

def create_admin_user(email, password, name, phone=''):
    """
    Create an admin user in DynamoDB.
    
    Args:
        email: Admin email address
        password: Admin password (will be hashed)
        name: Admin full name
        phone: Admin phone number (optional)
    """
    try:
        # Check if user already exists
        response = users_table.get_item(Key={'email': email})
        if 'Item' in response:
            print(f"❌ User with email {email} already exists!")
            print(f"   Current role: {response['Item'].get('role', 'unknown')}")
            
            # Ask if they want to update to admin
            update = input("Do you want to update this user to admin role? (yes/no): ").lower()
            if update == 'yes':
                users_table.update_item(
                    Key={'email': email},
                    UpdateExpression='SET #r = :r',
                    ExpressionAttributeNames={'#r': 'role'},
                    ExpressionAttributeValues={':r': 'admin'}
                )
                print(f"✅ User {email} updated to admin role!")
            return
        
        # Create new admin user
        admin_user = {
            'email': email,
            'password_hash': generate_password_hash(password),
            'name': name,
            'phone': phone,
            'role': 'admin',
            'is_active': True,
            'created_at': datetime.utcnow().isoformat()
        }
        
        users_table.put_item(Item=admin_user)
        print(f"✅ Admin user created successfully!")
        print(f"   Email: {email}")
        print(f"   Name: {name}")
        print(f"   Role: admin")
        print(f"\n🔐 You can now log in with these credentials at /login")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        raise

def main():
    print("=" * 60)
    print("FreshBakes - Admin User Creation")
    print("=" * 60)
    print()
    
    # Get admin details from user input
    print("Enter admin user details:")
    email = input("Email: ").strip().lower()
    password = input("Password: ").strip()
    name = input("Full Name: ").strip()
    phone = input("Phone (optional): ").strip()
    
    print()
    print("Creating admin user with:")
    print(f"  Email: {email}")
    print(f"  Name: {name}")
    print(f"  Phone: {phone if phone else 'Not provided'}")
    print()
    
    confirm = input("Proceed? (yes/no): ").lower()
    if confirm == 'yes':
        create_admin_user(email, password, name, phone)
    else:
        print("❌ Admin creation cancelled.")

if __name__ == '__main__':
    main()
