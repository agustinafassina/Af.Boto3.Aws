"""
List AWS Secrets Manager secrets per region: rotation, KMS key, dates, tags.
Does not read secret values.

Usage:
  python secretsmanager/read-secrets-manager-inventory.py
  python secretsmanager/read-secrets-manager-inventory.py sa-east-1
"""
import boto3
import csv
import json
import sys
from datetime import datetime

filter_region = sys.argv[1] if len(sys.argv) > 1 else None

ec2 = boto3.client('ec2', region_name='us-east-1')
all_regions = [r['RegionName'] for r in ec2.describe_regions()['Regions']]
regions = [filter_region] if filter_region else all_regions

if filter_region and filter_region not in all_regions:
    print(f"Invalid region: {filter_region}")
    sys.exit(1)


def fmt_dt(value):
    if not value:
        return ''
    if hasattr(value, 'strftime'):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    return str(value)


rows = []

for region in regions:
    print(f"Checking region: {region}")

    try:
        sm = boto3.client('secretsmanager', region_name=region)
        for page in sm.get_paginator('list_secrets').paginate():
            for entry in page.get('SecretList', []):
                name = entry.get('Name', '')
                try:
                    d = sm.describe_secret(SecretId=name)
                except Exception as e:
                    rows.append(
                        {
                            'Region': region,
                            'Name': name,
                            'ARN': entry.get('ARN', ''),
                            'DescribeError': str(e)[:200],
                            'Description': '',
                            'KmsKeyId': '',
                            'RotationEnabled': '',
                            'RotationLambdaARN': '',
                            'RotationRules': '',
                            'LastChangedDate': '',
                            'LastRotatedDate': '',
                            'LastAccessedDate': '',
                            'DeletedDate': '',
                            'OwningService': '',
                            'VersionCount': '',
                            'Tags': '',
                        }
                    )
                    continue

                tags = d.get('Tags') or []
                tags_str = '; '.join(f"{t['Key']}={t['Value']}" for t in tags)

                versions = d.get('VersionIdsToStages') or {}
                version_count = len(versions)

                rules = d.get('RotationRules')
                rules_str = json.dumps(rules, separators=(',', ':')) if rules else ''

                rows.append(
                    {
                        'Region': region,
                        'Name': d.get('Name', name),
                        'ARN': d.get('ARN', ''),
                        'DescribeError': '',
                        'Description': (d.get('Description') or '')[:300],
                        'KmsKeyId': d.get('KmsKeyId', ''),
                        'RotationEnabled': d.get('RotationEnabled', False),
                        'RotationLambdaARN': d.get('RotationLambdaARN', ''),
                        'RotationRules': rules_str,
                        'LastChangedDate': fmt_dt(d.get('LastChangedDate')),
                        'LastRotatedDate': fmt_dt(d.get('LastRotatedDate')),
                        'LastAccessedDate': fmt_dt(d.get('LastAccessedDate')),
                        'DeletedDate': fmt_dt(d.get('DeletedDate')),
                        'OwningService': d.get('OwningService', ''),
                        'VersionCount': version_count,
                        'Tags': tags_str,
                    }
                )

        n = len([r for r in rows if r['Region'] == region and not r.get('DescribeError')])
        n_err = len([r for r in rows if r['Region'] == region and r.get('DescribeError')])
        print(f"  Secrets in {region}: {n} ({n_err} describe errors)")

    except Exception as e:
        if 'Unsupported' in str(e) or 'AccessDenied' in str(e):
            print(f"  Skipping {region}: {e}")
        else:
            print(f"Error processing region {region}: {e}")
        continue

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'secrets_manager_inventory_{ts}.csv'

fieldnames = [
    'Region',
    'Name',
    'ARN',
    'DescribeError',
    'Description',
    'KmsKeyId',
    'RotationEnabled',
    'RotationLambdaARN',
    'RotationRules',
    'LastChangedDate',
    'LastRotatedDate',
    'LastAccessedDate',
    'DeletedDate',
    'OwningService',
    'VersionCount',
    'Tags',
]

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)

no_rotation = sum(1 for r in rows if not r.get('DescribeError') and r.get('RotationEnabled') is False)
print(f"\nCSV exported: {csv_filename}")
print(f"Total secret rows: {len(rows)}")
print(f"Secrets with RotationEnabled=False: {no_rotation}")
