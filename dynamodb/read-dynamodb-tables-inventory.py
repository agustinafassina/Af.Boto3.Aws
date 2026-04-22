"""
List DynamoDB tables per region: billing mode, size, item count, encryption,
streams, TTL, and point-in-time recovery (PITR).

Usage:
  python dynamodb/read-dynamodb-tables-inventory.py
  python dynamodb/read-dynamodb-tables-inventory.py sa-east-1
"""
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
        ddb = boto3.client('dynamodb', region_name=region)

        table_names = []
        for page in ddb.get_paginator('list_tables').paginate():
            table_names.extend(page.get('TableNames', []))

        if not table_names:
            print(f"  No tables in {region}")
            continue

        for name in table_names:
            try:
                t = ddb.describe_table(TableName=name)['Table']
            except Exception as e:
                rows.append(
                    {
                        'Region': region,
                        'TableName': name,
                        'DescribeError': str(e)[:200],
                        'TableStatus': '',
                        'TableArn': '',
                        'BillingMode': '',
                        'ReadCapacityUnits': '',
                        'WriteCapacityUnits': '',
                        'TableSizeBytes': '',
                        'ItemCount': '',
                        'StreamEnabled': '',
                        'SSEType': '',
                        'TTLStatus': '',
                        'PITRStatus': '',
                        'GSI_Count': '',
                        'LSI_Count': '',
                        'CreationDateTime': '',
                    }
                )
                continue

            billing = t.get('BillingModeSummary') or {}
            billing_mode = billing.get('BillingMode', 'PROVISIONED')
            prov = t.get('ProvisionedThroughput') or {}
            rcu = prov.get('ReadCapacityUnits', '')
            wcu = prov.get('WriteCapacityUnits', '')

            stream = t.get('StreamSpecification') or {}
            stream_on = stream.get('StreamEnabled', False)

            sse = (t.get('SSEDescription') or {}).get('SSEType', '')

            gsi = len(t.get('GlobalSecondaryIndexes') or [])
            lsi = len(t.get('LocalSecondaryIndexes') or [])

            ttl_status = ''
            try:
                ttl = ddb.describe_time_to_live(TableName=name).get('TimeToLiveDescription') or {}
                ttl_status = ttl.get('TimeToLiveStatus', '')
            except Exception:
                ttl_status = 'UNKNOWN'

            pitr_status = ''
            try:
                pitr = ddb.describe_continuous_backups(TableName=name).get('ContinuousBackupsDescription') or {}
                pdesc = pitr.get('PointInTimeRecoveryDescription') or {}
                pitr_status = pdesc.get('PointInTimeRecoveryStatus', '')
            except Exception:
                pitr_status = 'UNKNOWN'

            rows.append(
                {
                    'Region': region,
                    'TableName': name,
                    'DescribeError': '',
                    'TableStatus': t.get('TableStatus', ''),
                    'TableArn': t.get('TableArn', ''),
                    'BillingMode': billing_mode,
                    'ReadCapacityUnits': rcu,
                    'WriteCapacityUnits': wcu,
                    'TableSizeBytes': t.get('TableSizeBytes', ''),
                    'ItemCount': t.get('ItemCount', ''),
                    'StreamEnabled': stream_on,
                    'SSEType': sse,
                    'TTLStatus': ttl_status,
                    'PITRStatus': pitr_status,
                    'GSI_Count': gsi,
                    'LSI_Count': lsi,
                    'CreationDateTime': fmt_dt(t.get('CreationDateTime')),
                }
            )

        n = len([r for r in rows if r['Region'] == region and not r.get('DescribeError')])
        print(f"  Tables in {region}: {n}")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'dynamodb_tables_inventory_{ts}.csv'

fieldnames = [
    'Region',
    'TableName',
    'DescribeError',
    'TableStatus',
    'TableArn',
    'BillingMode',
    'ReadCapacityUnits',
    'WriteCapacityUnits',
    'TableSizeBytes',
    'ItemCount',
    'StreamEnabled',
    'SSEType',
    'TTLStatus',
    'PITRStatus',
    'GSI_Count',
    'LSI_Count',
    'CreationDateTime',
]

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)

pitr_enabled = sum(1 for r in rows if not r.get('DescribeError') and r.get('PITRStatus') == 'ENABLED')

print(f"\nCSV exported: {csv_filename}")
print(f"Total table rows: {len(rows)}")
print(f"PITR ENABLED: {pitr_enabled}")
