import boto3
import csv
from datetime import datetime

iam = boto3.client('iam')

users_without_mfa = []

print("Listing IAM users and checking MFA...")

paginator = iam.get_paginator('list_users')
for page in paginator.paginate():
    for user in page['Users']:
        user_name = user['UserName']

        try:
            mfa_response = iam.list_mfa_devices(UserName=user_name)
            if mfa_response.get('MFADevices'):
                continue  # User has MFA, skip
        except Exception as e:
            print(f"Error checking MFA for {user_name}: {e}")
            continue

        # User has no MFA devices
        create_date = user.get('CreateDate', '')
        if create_date:
            create_date = create_date.strftime('%Y-%m-%d %H:%M:%S')
        password_last_used = user.get('PasswordLastUsed', '')
        if password_last_used:
            password_last_used = password_last_used.strftime('%Y-%m-%d %H:%M:%S')

        users_without_mfa.append({
            'UserName': user_name,
            'UserId': user.get('UserId', ''),
            'Arn': user.get('Arn', ''),
            'CreateDate': create_date,
            'PasswordLastUsed': password_last_used,
        })

        print(f"  No MFA: {user_name}")

# Export to CSV
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'iam_users_without_mfa_{ts}.csv'

csv_columns = ['UserName', 'UserId', 'Arn', 'CreateDate', 'PasswordLastUsed']

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=csv_columns)
    writer.writeheader()
    writer.writerows(users_without_mfa)

print(f"\nCSV exported: {csv_filename}")
print(f"Total users without MFA: {len(users_without_mfa)}")
