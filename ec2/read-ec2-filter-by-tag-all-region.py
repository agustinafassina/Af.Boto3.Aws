import boto3

ec2 = boto3.client('ec2')

regions_response = ec2.describe_regions()
regions = [region['RegionName'] for region in regions_response['Regions']]

for region in regions:
    print(f"Checking region: {region}")

    regional_ec2 = boto3.client('ec2', region_name=region)

    response = regional_ec2.describe_instances()

    instances_without_project_tag = []

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            if 'Tags' not in instance or not any(tag['Key'] == 'Project' for tag in instance['Tags']):
                instances_without_project_tag.append(instance['InstanceId'])

    if instances_without_project_tag:
        print(f"Instances without 'Project' tag in {region}:")
        for instance_id in instances_without_project_tag:
            print(f"  - {instance_id}")
    else:
        print(f"No instances without 'Project' tag in region: {region}")