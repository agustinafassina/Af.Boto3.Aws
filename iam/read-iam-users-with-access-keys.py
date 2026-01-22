import boto3
import csv
from datetime import datetime

iam = boto3.client('iam')

# List to store users with access keys
users_with_keys_data = []

# Function to get access keys for a user
def get_user_access_keys(user_name):
    try:
        response = iam.list_access_keys(UserName=user_name)
        return response.get('AccessKeyMetadata', [])
    except Exception as e:
        print(f"Error retrieving access keys for {user_name}: {e}")
        return []

# List all users
print("Listing all IAM users...")
paginator = iam.get_paginator('list_users')

for page in paginator.paginate():
    for user in page['Users']:
        user_name = user['UserName']
        
        # Get access keys for this user
        access_keys = get_user_access_keys(user_name)
        
        if access_keys:
            # User has at least one access key
            for key in access_keys:
                access_key_id = key['AccessKeyId']
                status = key['Status']
                create_date = key['CreateDate']
                
                # Calculate age of the key in days
                age_days = (datetime.now(create_date.tzinfo) - create_date).days
                
                # Format creation date
                create_date_str = create_date.strftime('%Y-%m-%d %H:%M:%S')
                
                users_with_keys_data.append({
                    'UserName': user_name,
                    'AccessKeyId': access_key_id,
                    'Status': status,
                    'CreateDate': create_date_str,
                    'AgeInDays': age_days,
                    'UserId': user['UserId'],
                    'UserArn': user['Arn']
                })
            
            print(f"User {user_name} has {len(access_keys)} access key(s)")

# Export to CSV
if users_with_keys_data:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'iam_users_with_access_keys_{timestamp}.csv'
    
    csv_columns = [
        'UserName',
        'AccessKeyId',
        'Status',
        'CreateDate',
        'AgeInDays',
        'UserId',
        'UserArn'
    ]
    
    with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=csv_columns)
        writer.writeheader()
        
        for row in users_with_keys_data:
            writer.writerow(row)
    
    print(f"\nReport generated: {csv_filename}")
    print(f"Total users with access keys: {len(set(row['UserName'] for row in users_with_keys_data))}")
    print(f"Total access keys found: {len(users_with_keys_data)}")
    
    # Show summary by status
    active_keys = len([row for row in users_with_keys_data if row['Status'] == 'Active'])
    inactive_keys = len([row for row in users_with_keys_data if row['Status'] == 'Inactive'])
    print(f"Active keys: {active_keys}")
    print(f"Inactive keys: {inactive_keys}")
    
    # Show oldest keys
    if users_with_keys_data:
        oldest_key = max(users_with_keys_data, key=lambda x: x['AgeInDays'])
        print(f"\nOldest access key:")
        print(f"  User: {oldest_key['UserName']}")
        print(f"  Key ID: {oldest_key['AccessKeyId']}")
        print(f"  Age: {oldest_key['AgeInDays']} days")
        print(f"  Created: {oldest_key['CreateDate']}")
else:
    print("\nNo users with access keys found.")

