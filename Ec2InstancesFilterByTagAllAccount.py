import boto3

# Crear un cliente de EC2 para poder listar regiones
ec2 = boto3.client('ec2')

# Obtener todas las regiones
regions_response = ec2.describe_regions()
regions = [region['RegionName'] for region in regions_response['Regions']]

def check_ec2_instances(region):
    print(f"\nChecking EC2 instances in region: {region}")
    regional_ec2 = boto3.client('ec2', region_name=region)
    response = regional_ec2.describe_instances()

    instances_without_project_tag = []

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            if 'Tags' not in instance or not any(tag['Key'] == 'Project' for tag in instance['Tags']):
                instances_without_project_tag.append(instance['InstanceId'])

    if instances_without_project_tag:
        print(f"Instances without 'Project' tag: {instances_without_project_tag}")

def check_ebs_volumes(region):
    print(f"\nChecking EBS volumes in region: {region}")
    regional_ec2 = boto3.client('ec2', region_name=region)
    response = regional_ec2.describe_volumes()

    volumes_without_project_tag = []

    for volume in response['Volumes']:
        if 'Tags' not in volume or not any(tag['Key'] == 'Project' for tag in volume['Tags']):
            volumes_without_project_tag.append(volume['VolumeId'])

    if volumes_without_project_tag:
        print(f"EBS Volumes without 'Project' tag: {volumes_without_project_tag}")

def check_security_groups(region):
    print(f"\nChecking Security Groups in region: {region}")
    regional_ec2 = boto3.client('ec2', region_name=region)
    response = regional_ec2.describe_security_groups()

    security_groups_without_project_tag = []

    for group in response['SecurityGroups']:
        if 'Tags' not in group or not any(tag['Key'] == 'Project' for tag in group['Tags']):
            security_groups_without_project_tag.append(group['GroupId'])

    if security_groups_without_project_tag:
        print(f"Security Groups without 'Project' tag: {security_groups_without_project_tag}")

def check_elastic_ips(region):
    print(f"\nChecking Elastic IPs in region: {region}")
    regional_ec2 = boto3.client('ec2', region_name=region)
    response = regional_ec2.describe_addresses()

    elastic_ips_without_project_tag = []

    for address in response['Addresses']:
        if 'Tags' not in address or not any(tag['Key'] == 'Project' for tag in address['Tags']):
            elastic_ips_without_project_tag.append(address['PublicIp'])

    if elastic_ips_without_project_tag:
        print(f"Elastic IPs without 'Project' tag: {elastic_ips_without_project_tag}")

def check_ecr_repositories(region):
    print(f"\nChecking ECR Repositories in region: {region}")
    regional_ecr = boto3.client('ecr', region_name=region)
    response = regional_ecr.describe_repositories()

    repositories_without_project_tag = []

    for repository in response['repositories']:
        # Verifica si el tag "Project" no está presente (no se utiliza Tags para ECR)
        if not hasattr(repository, 'tags') or not any(tag['Key'] == 'Project' for tag in repository.get('tags', [])):
            repositories_without_project_tag.append(repository['repositoryName'])

    if repositories_without_project_tag:
        print(f"ECR Repositories without 'Project' tag: {repositories_without_project_tag}")

def check_configuration_rules(region):
    print(f"\nChecking Config Rules in region: {region}")
    regional_config = boto3.client('config', region_name=region)
    response = regional_config.describe_config_rules()

    rules_without_project_tag = []

    for rule in response['ConfigRules']:
        rule_tags = regional_config.list_tags_for_resource(ResourceArn=rule['ConfigRuleArn'])
        if 'Tags' not in rule_tags or not any(tag['Key'] == 'Project' for tag in rule_tags.get('Tags', [])):
            rules_without_project_tag.append(rule['ConfigRuleName'])

    if rules_without_project_tag:
        print(f"Config Rules without 'Project' tag: {rules_without_project_tag}")

# Iterar sobre todas las regiones
for region in regions:
    check_ec2_instances(region)
    check_ebs_volumes(region)
    check_security_groups(region)
    check_elastic_ips(region)
    check_ecr_repositories(region)
    check_configuration_rules(region)