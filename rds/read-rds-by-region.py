import boto3
import csv
import sys
from datetime import datetime

# Optional: filter by a single region (e.g. python read-rds-by-region.py sa-east-1)
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
                endpoint = db.get('Endpoint') or {}
                endpoint_address = endpoint.get('Address', '')
                endpoint_port = endpoint.get('Port', '')

                rds_data.append({
                    'Region': region,
                    'DBInstanceIdentifier': db.get('DBInstanceIdentifier', ''),
                    'Engine': db.get('Engine', ''),
                    'EngineVersion': db.get('EngineVersion', ''),
                    'DBInstanceClass': db.get('DBInstanceClass', ''),
                    'DBInstanceStatus': db.get('DBInstanceStatus', ''),
                    'EndpointAddress': endpoint_address,
                    'EndpointPort': str(endpoint_port) if endpoint_port else '',
                    'AllocatedStorage': db.get('AllocatedStorage', ''),
                    'MultiAZ': db.get('MultiAZ', False),
                    'VpcId': db.get('DBSubnetGroup', {}).get('VpcId', '') if db.get('DBSubnetGroup') else '',
                    'AvailabilityZone': db.get('AvailabilityZone', ''),
                    'DBInstanceArn': db.get('DBInstanceArn', ''),
                })

        count = len([r for r in rds_data if r['Region'] == region])
        print(f"  RDS instances in {region}: {count}")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

# Export to CSV
if rds_data:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'rds_by_region_{timestamp}.csv'

    csv_columns = [
        'Region',
        'DBInstanceIdentifier',
        'Engine',
        'EngineVersion',
        'DBInstanceClass',
        'DBInstanceStatus',
        'EndpointAddress',
        'EndpointPort',
        'AllocatedStorage',
        'MultiAZ',
        'VpcId',
        'AvailabilityZone',
        'DBInstanceArn',
    ]

    with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerows(rds_data)

    print(f"\nReport generated: {csv_filename}")
    print(f"Total RDS instances: {len(rds_data)}")
else:
    print("\nNo RDS instances found.")
