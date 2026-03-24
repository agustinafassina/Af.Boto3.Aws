import boto3
import csv
from datetime import datetime

IAM_ACCESS_KEY_MAX_AGE_DAYS = 90

iam = boto3.client('iam')

old_keys_data = []


def get_user_access_keys(user_name):
    try:
        response = iam.list_access_keys(UserName=user_name)
        return response.get('AccessKeyMetadata', [])
    except Exception as e:
        print(f"Error retrieving access keys for {user_name}: {e}")
        return []


print(f"Listing IAM access keys older than {IAM_ACCESS_KEY_MAX_AGE_DAYS} days...")

paginator = iam.get_paginator('list_users')
for page in paginator.paginate():
    for user in page['Users']:
        user_name = user['UserName']
        access_keys = get_user_access_keys(user_name)

        for key in access_keys:
            create_date = key['CreateDate']
            age_days = (datetime.now(create_date.tzinfo) - create_date).days

            if age_days < IAM_ACCESS_KEY_MAX_AGE_DAYS:
                continue

            old_keys_data.append({
                'UserName': user_name,
                'AccessKeyId': key['AccessKeyId'],
                'Status': key['Status'],
                'CreateDate': create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'AgeInDays': age_days,
                'UserId': user['UserId'],
                'UserArn': user['Arn'],
            })
            print(f"  Key older than {IAM_ACCESS_KEY_MAX_AGE_DAYS} days: {user_name} / {key['AccessKeyId']} ({age_days} days)")

# Export to CSV
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'iam_access_keys_older_than_{IAM_ACCESS_KEY_MAX_AGE_DAYS}_days_{ts}.csv'

csv_columns = [
    'UserName',
    'AccessKeyId',
    'Status',
    'CreateDate',
    'AgeInDays',
    'UserId',
    'UserArn',
]

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=csv_columns)
    writer.writeheader()
    writer.writerows(old_keys_data)

print(f"\nCSV exported: {csv_filename}")
print(f"Total access keys older than {IAM_ACCESS_KEY_MAX_AGE_DAYS} days: {len(old_keys_data)}")
