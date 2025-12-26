import boto3
import json

iam = boto3.client('iam')
response = iam.list_users()

users_list = []

for user in response['Users']:
    user_info = {
        'UserName': user['UserName'],
        'UserId': user['UserId'],
        'Arn': user['Arn'],
        'CreateDate': str(user['CreateDate']),
        'Groups': [],
        'Roles': []
    }
    groups_response = iam.list_groups_for_user(UserName=user['UserName'])
    user_info['Groups'] = [g['GroupName'] for g in groups_response['Groups']]

    response_roles = iam.list_attached_user_policies(UserName=user['UserName'])
    user_info['Roles'] = [p['PolicyName'] for p in response_roles['AttachedPolicies']]

    users_list.append(user_info)

print(json.dumps(users_list, indent=4))