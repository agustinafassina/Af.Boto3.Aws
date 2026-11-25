import boto3
import json

iam = boto3.client('iam')


def paginate(method, key, **kwargs):
    items = []
    for page in iam.get_paginator(method).paginate(**kwargs):
        items.extend(page[key])
    return items


users_list = []

for user in paginate('list_users', 'Users'):
    user_name = user['UserName']
    groups = paginate('list_groups_for_user', 'Groups', UserName=user_name)
    policies = paginate('list_attached_user_policies', 'AttachedPolicies', UserName=user_name)

    users_list.append({
        'UserName': user_name,
        'UserId': user['UserId'],
        'Arn': user['Arn'],
        'CreateDate': str(user['CreateDate']),
        'Groups': [g['GroupName'] for g in groups],
        'Roles': [p['PolicyName'] for p in policies],
    })

print(json.dumps(users_list, indent=4))
