import boto3

ec2 = boto3.client('ec2')

regions_response = ec2.describe_regions()
regions = [region['RegionName'] for region in regions_response['Regions']]


def has_project_tag(tags, key_name='Key'):
    return any(tag[key_name] == 'Project' for tag in tags or [])


def paginate(client, method, key, **kwargs):
    items = []
    for page in client.get_paginator(method).paginate(**kwargs):
        items.extend(page[key])
    return items


def check_ec2_instances(region):
    print(f"\nChecking EC2 instances in region: {region}")
    regional_ec2 = boto3.client('ec2', region_name=region)

    instances_without_project_tag = []

    for reservation in paginate(regional_ec2, 'describe_instances', 'Reservations'):
        for instance in reservation['Instances']:
            if not has_project_tag(instance.get('Tags')):
                instances_without_project_tag.append(instance['InstanceId'])

    if instances_without_project_tag:
        print(f"Instances without 'Project' tag: {instances_without_project_tag}")


def check_ebs_volumes(region):
    print(f"\nChecking EBS volumes in region: {region}")
    regional_ec2 = boto3.client('ec2', region_name=region)

    volumes_without_project_tag = [
        volume['VolumeId']
        for volume in paginate(regional_ec2, 'describe_volumes', 'Volumes')
        if not has_project_tag(volume.get('Tags'))
    ]

    if volumes_without_project_tag:
        print(f"EBS Volumes without 'Project' tag: {volumes_without_project_tag}")


def check_security_groups(region):
    print(f"\nChecking Security Groups in region: {region}")
    regional_ec2 = boto3.client('ec2', region_name=region)

    security_groups_without_project_tag = [
        group['GroupId']
        for group in paginate(regional_ec2, 'describe_security_groups', 'SecurityGroups')
        if not has_project_tag(group.get('Tags'))
    ]

    if security_groups_without_project_tag:
        print(f"Security Groups without 'Project' tag: {security_groups_without_project_tag}")


def check_elastic_ips(region):
    print(f"\nChecking Elastic IPs in region: {region}")
    regional_ec2 = boto3.client('ec2', region_name=region)
    # describe_addresses is not paginated
    response = regional_ec2.describe_addresses()

    elastic_ips_without_project_tag = [
        address['PublicIp']
        for address in response['Addresses']
        if not has_project_tag(address.get('Tags'))
    ]

    if elastic_ips_without_project_tag:
        print(f"Elastic IPs without 'Project' tag: {elastic_ips_without_project_tag}")


def check_ecr_repositories(region):
    print(f"\nChecking ECR Repositories in region: {region}")
    regional_ecr = boto3.client('ecr', region_name=region)

    repositories_without_project_tag = []

    # describe_repositories does not return tags; fetch them per repository
    for repository in paginate(regional_ecr, 'describe_repositories', 'repositories'):
        tags = regional_ecr.list_tags_for_resource(resourceArn=repository['repositoryArn']).get('tags', [])
        if not has_project_tag(tags):
            repositories_without_project_tag.append(repository['repositoryName'])

    if repositories_without_project_tag:
        print(f"ECR Repositories without 'Project' tag: {repositories_without_project_tag}")


def check_configuration_rules(region):
    print(f"\nChecking Config Rules in region: {region}")
    regional_config = boto3.client('config', region_name=region)

    rules_without_project_tag = []

    for rule in paginate(regional_config, 'describe_config_rules', 'ConfigRules'):
        rule_tags = regional_config.list_tags_for_resource(ResourceArn=rule['ConfigRuleArn'])
        if not has_project_tag(rule_tags.get('Tags')):
            rules_without_project_tag.append(rule['ConfigRuleName'])

    if rules_without_project_tag:
        print(f"Config Rules without 'Project' tag: {rules_without_project_tag}")


for region in regions:
    check_ec2_instances(region)
    check_ebs_volumes(region)
    check_security_groups(region)
    check_elastic_ips(region)
    check_ecr_repositories(region)
    check_configuration_rules(region)
