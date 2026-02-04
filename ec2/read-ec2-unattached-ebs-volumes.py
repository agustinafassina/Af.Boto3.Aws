import boto3
import csv
from datetime import datetime

# Get all regions
ec2 = boto3.client('ec2', region_name='sa-east-1')
regions_response = ec2.describe_regions()
regions = [region['RegionName'] for region in regions_response['Regions']]

unattached_volumes = []

for region in regions:
    print(f"Checking region: {region}")

    try:
        regional_ec2 = boto3.client('ec2', region_name=region)
        paginator = regional_ec2.get_paginator('describe_volumes')

        for page in paginator.paginate():
            for vol in page.get('Volumes', []):
                # Unattached = state is 'available' (no instance attached)
                if vol.get('State') != 'available':
                    continue

                create_time = vol.get('CreateTime', '')
                if create_time:
                    create_time = create_time.strftime('%Y-%m-%d %H:%M:%S')

                tags = vol.get('Tags') or []
                tags_str = '; '.join(f"{t['Key']}={t['Value']}" for t in tags)

                unattached_volumes.append({
                    'Region': region,
                    'VolumeId': vol.get('VolumeId', ''),
                    'SizeGb': vol.get('Size', ''),
                    'VolumeType': vol.get('VolumeType', ''),
                    'State': vol.get('State', ''),
                    'AvailabilityZone': vol.get('AvailabilityZone', ''),
                    'CreateTime': create_time,
                    'SnapshotId': vol.get('SnapshotId', ''),
                    'Tags': tags_str,
                })

        count = len([v for v in unattached_volumes if v['Region'] == region])
        print(f"  Unattached EBS volumes in {region}: {count}")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

# Export to CSV (always generate file, with or without rows)
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'unattached_ebs_volumes_{ts}.csv'

csv_columns = [
    'Region',
    'VolumeId',
    'SizeGb',
    'VolumeType',
    'State',
    'AvailabilityZone',
    'CreateTime',
    'SnapshotId',
    'Tags',
]

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=csv_columns)
    writer.writeheader()
    writer.writerows(unattached_volumes)

print(f"\nCSV exported: {csv_filename}")
if unattached_volumes:
    total_gb = sum(v['SizeGb'] for v in unattached_volumes)
    print(f"Total unattached volumes: {len(unattached_volumes)}")
    print(f"Total size (Gb): {total_gb}")
else:
    print("No unattached EBS volumes found (CSV has headers only).")
