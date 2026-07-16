import boto3
import csv
import sys
from datetime import datetime

filter_region = sys.argv[1] if len(sys.argv) > 1 else None

ec2 = boto3.client('ec2', region_name='us-east-1')
all_regions = [r['RegionName'] for r in ec2.describe_regions()['Regions']]
regions = [filter_region] if filter_region else all_regions

if filter_region and filter_region not in all_regions:
    print(f"Invalid region: {filter_region}")
    sys.exit(1)


def get_tags(lambda_client, function_arn):
    try:
        tags = lambda_client.list_tags(Resource=function_arn).get('Tags') or {}
        return '; '.join(f"{k}={v}" for k, v in sorted(tags.items()))
    except Exception:
        return ''


rows = []

for region in regions:
    print(f"Checking region: {region}")

    try:
        lam = boto3.client('lambda', region_name=region)
        for page in lam.get_paginator('list_functions').paginate():
            for fn in page.get('Functions', []):
                name = fn.get('FunctionName', '')
                arn = fn.get('FunctionArn', '')
                vpc = fn.get('VpcConfig') or {}
                subnet_ids = vpc.get('SubnetIds') or []
                sg_ids = vpc.get('SecurityGroupIds') or []
                vpc_id = vpc.get('VpcId', '')

                last_modified = fn.get('LastModified', '')
                architectures = ','.join(fn.get('Architectures') or [])
                layers = len(fn.get('Layers') or [])
                ephemeral = (fn.get('EphemeralStorage') or {}).get('Size', '')

                rows.append(
                    {
                        'Region': region,
                        'FunctionName': name,
                        'FunctionArn': arn,
                        'Runtime': fn.get('Runtime', ''),
                        'Handler': fn.get('Handler', ''),
                        'PackageType': fn.get('PackageType', ''),
                        'Role': fn.get('Role', ''),
                        'MemorySize': fn.get('MemorySize', ''),
                        'Timeout': fn.get('Timeout', ''),
                        'EphemeralStorageMb': ephemeral,
                        'Architectures': architectures,
                        'LastModified': last_modified,
                        'CodeSize': fn.get('CodeSize', ''),
                        'Description': (fn.get('Description') or '')[:200],
                        'VpcId': vpc_id,
                        'SubnetCount': len(subnet_ids),
                        'SecurityGroupCount': len(sg_ids),
                        'LayerCount': layers,
                        'State': (fn.get('State') or ''),
                        'LastUpdateStatus': fn.get('LastUpdateStatus', ''),
                        'Tags': get_tags(lam, arn),
                    }
                )

        n = len([r for r in rows if r['Region'] == region])
        print(f"  Lambda functions in {region}: {n}")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'lambda_functions_inventory_{ts}.csv'

fieldnames = [
    'Region',
    'FunctionName',
    'FunctionArn',
    'Runtime',
    'Handler',
    'PackageType',
    'Role',
    'MemorySize',
    'Timeout',
    'EphemeralStorageMb',
    'Architectures',
    'LastModified',
    'CodeSize',
    'Description',
    'VpcId',
    'SubnetCount',
    'SecurityGroupCount',
    'LayerCount',
    'State',
    'LastUpdateStatus',
    'Tags',
]

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)

print(f"\nCSV exported: {csv_filename}")
print(f"Total Lambda functions: {len(rows)}")
