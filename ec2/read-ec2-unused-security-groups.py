import boto3
import csv
from datetime import datetime

# Get all regions (use a region for the initial client if no default is set)
ec2 = boto3.client('ec2', region_name='us-east-1')
regions_response = ec2.describe_regions()
regions = [region['RegionName'] for region in regions_response['Regions']]

# List to store all security groups with InUse flag
sgs_data = []


def get_used_security_group_ids(regional_ec2):
    """Get set of security group IDs that are attached to at least one network interface."""
    used_sg_ids = set()
    paginator = regional_ec2.get_paginator('describe_network_interfaces')
    for page in paginator.paginate():
        for eni in page.get('NetworkInterfaces', []):
            for group in eni.get('Groups', []):
                used_sg_ids.add(group['GroupId'])
    return used_sg_ids


for region in regions:
    print(f"Checking region: {region}")

    try:
        regional_ec2 = boto3.client('ec2', region_name=region)

        # Get all security group IDs that are in use (attached to an ENI)
        used_sg_ids = get_used_security_group_ids(regional_ec2)

        # List all security groups
        paginator = regional_ec2.get_paginator('describe_security_groups')
        for page in paginator.paginate():
            for sg in page['SecurityGroups']:
                group_id = sg['GroupId']
                group_name = sg['GroupName']
                vpc_id = sg.get('VpcId', 'EC2-Classic')
                in_use = group_id in used_sg_ids

                sgs_data.append({
                    'Region': region,
                    'GroupId': group_id,
                    'GroupName': group_name,
                    'VpcId': vpc_id,
                    'Description': sg.get('Description', ''),
                    'IsDefault': sg.get('GroupName') == 'default',
                    'InUse': 'Yes' if in_use else 'No',
                })

        count_region = len([r for r in sgs_data if r['Region'] == region])
        count_unused = len([r for r in sgs_data if r['Region'] == region and r['InUse'] == 'No'])
        print(f"  Security groups in {region}: {count_region} (unused: {count_unused})")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

# Export to CSV
if sgs_data:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'unused_security_groups_{timestamp}.csv'

    csv_columns = [
        'Region',
        'GroupId',
        'GroupName',
        'VpcId',
        'Description',
        'IsDefault',
        'InUse',
    ]

    with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerows(sgs_data)

    print(f"\nReport generated: {csv_filename}")
    print(f"Total security groups: {len(sgs_data)}")
    unused_count = sum(1 for r in sgs_data if r['InUse'] == 'No')
    print(f"  In use: {len(sgs_data) - unused_count}")
    print(f"  Not in use: {unused_count}")
    default_count = sum(1 for r in sgs_data if r['IsDefault'])
    if default_count:
        print(f"  (including {default_count} default SGs - cannot be deleted)")
else:
    print("\nNo security groups found.")
