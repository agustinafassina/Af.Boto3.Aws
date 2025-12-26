import boto3
import pandas as pd

iam = boto3.client('iam')

def get_user_tags(user_name):
    response = iam.list_user_tags(UserName=user_name)
    return {tag['Key']: tag['Value'] for tag in response['Tags']}

def get_user_policies(user_name):
    policies = []

    response = iam.list_attached_user_policies(UserName=user_name)
    for policy in response['AttachedPolicies']:
        policies.append(policy['PolicyName'])

    inline_response = iam.list_user_policies(UserName=user_name)
    policies.extend(inline_response['PolicyNames'])
    return policies


def get_group_permissions(group_name):
    permissions = []

    response = iam.list_attached_group_policies(GroupName=group_name)
    for policy in response['AttachedPolicies']:
        permissions.append(policy['PolicyName'])

    inline_response = iam.list_group_policies(GroupName=group_name)
    permissions.extend(inline_response['PolicyNames'])
    return permissions

def get_iam_users():
    users = []
    paginator = iam.get_paginator('list_users')
    for page in paginator.paginate():
        for user in page['Users']:
            user_name = user['UserName']

            groups_response = iam.list_groups_for_user(UserName=user_name)
            groups = [group['GroupName'] for group in groups_response['Groups']]

            user_policies = get_user_policies(user_name)

            group_permissions = []
            for group in groups:
                group_permissions.extend(get_group_permissions(group))

            tags = get_user_tags(user_name)
            project_name = tags.get('Project', '')
            project_status = tags.get('ProjectStatus', '')
            project_service = tags.get('ProjectService', '')
            project_description = tags.get('ProjectDescription', '')

            users.append({
                'UserName': user_name,
                'Groups': ', '.join(groups),
                'UserPolicies': ', '.join(user_policies),
                'GroupPermissions': ', '.join(set(group_permissions)),
                'Tag Project': project_name,
                'Tag ProjectStatus': project_status,
                'Tag ProjectService': project_service,
                'Tag ProjectDescription': project_description
            })

    return users

users_data = get_iam_users()

df = pd.DataFrame(users_data)

df.to_csv('users_iam_tags_permisos.csv', index=False)

print("Success export file users_iam_tags_permisos.csv")