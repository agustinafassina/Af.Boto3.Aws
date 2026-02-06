import boto3
import csv
import sys
from datetime import datetime

# Optional: filter by a single region (e.g. python read-rds-public-private.py sa-east-1)
filter_region = sys.argv[1] if len(sys.argv) > 1 else None

# Get regions
ec2 = boto3.client('ec2', region_name='us-east-1')
regions_response = ec2.describe_regions()
all_regions = [r['RegionName'] for r in regions_response['Regions']]
regions = [filter_region] if filter_region else all_regions

if filter_region and filter_region not in all_regions:
    print(f"Invalid region: {filter_region}")
    sys.exit(1)

rds_data = []

for region in regions:
    print(f"Checking region: {region}")

    try:
        rds = boto3.client('rds', region_name=region)
        paginator = rds.get_paginator('describe_db_instances')

        for page in paginator.paginate():
            for db in page.get('DBInstances', []):
                publicly_accessible = db.get('PubliclyAccessible', False)
                accessibility = 'Public' if publicly_accessible else 'Private'

                endpoint = db.get('Endpoint') or {}
                endpoint_address = endpoint.get('Address', '')
                endpoint_port = endpoint.get('Port', '')

                rds_data.append({
                    'Region': region,
                    'DBInstanceIdentifier': db.get('DBInstanceIdentifier', ''),
                    'Accessibility': accessibility,
                    'PubliclyAccessible': publicly_accessible,
                    'Engine': db.get('Engine', ''),
                    'EngineVersion': db.get('EngineVersion', ''),
                    'DBInstanceClass': db.get('DBInstanceClass', ''),
                    'DBInstanceStatus': db.get('DBInstanceStatus', ''),
                    'EndpointAddress': endpoint_address,
                    'EndpointPort': str(endpoint_port) if endpoint_port else '',
                    'VpcId': db.get('DBSubnetGroup', {}).get('VpcId', '') if db.get('DBSubnetGroup') else '',
                    'AvailabilityZone': db.get('AvailabilityZone', ''),
                })

        count = len([r for r in rds_data if r['Region'] == region])
        print(f"  RDS instances in {region}: {count}")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

# Export to CSV
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'rds_public_private_{ts}.csv'

csv_columns = [
    'Region',
    'DBInstanceIdentifier',
    'Accessibility',
    'PubliclyAccessible',
    'Engine',
    'EngineVersion',
    'DBInstanceClass',
    'DBInstanceStatus',
    'EndpointAddress',
    'EndpointPort',
    'VpcId',
    'AvailabilityZone',
]

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=csv_columns)
    writer.writeheader()
    writer.writerows(rds_data)

print(f"\nCSV exported: {csv_filename}")
print(f"Total RDS instances: {len(rds_data)}")

if rds_data:
    public_count = sum(1 for r in rds_data if r['Accessibility'] == 'Public')
    private_count = len(rds_data) - public_count
    print(f"  Public:  {public_count}")
    print(f"  Private: {private_count}")
