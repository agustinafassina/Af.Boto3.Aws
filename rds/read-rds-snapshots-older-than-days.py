import boto3
import csv
import sys
from datetime import datetime

# List RDS snapshots (DB instance + Aurora cluster, manual + automated) owned by
# this account that are older than N days (default 90).
# Usage:
#   python rds/read-rds-snapshots-older-than-days.py              -> 90 days, all regions
#   python rds/read-rds-snapshots-older-than-days.py 30           -> 30 days, all regions
#   python rds/read-rds-snapshots-older-than-days.py 30 sa-east-1 -> 30 days, one region
SNAPSHOT_MIN_AGE_DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 90
filter_region = sys.argv[2] if len(sys.argv) > 2 else None

ec2 = boto3.client('ec2', region_name='us-east-1')
all_regions = [r['RegionName'] for r in ec2.describe_regions()['Regions']]

if filter_region and filter_region not in all_regions:
    print(f"Invalid region: {filter_region}")
    sys.exit(1)

regions = [filter_region] if filter_region else all_regions

old_snapshots = []


def age_in_days(create_time):
    return (datetime.now(create_time.tzinfo) - create_time).days


for region in regions:
    print(f"Checking region: {region}")

    try:
        rds = boto3.client('rds', region_name=region)

        # DB instance snapshots
        paginator = rds.get_paginator('describe_db_snapshots')
        for page in paginator.paginate():
            for snap in page.get('DBSnapshots', []):
                create_time = snap.get('SnapshotCreateTime')
                if not create_time:
                    continue  # snapshot still being created
                age_days = age_in_days(create_time)
                if age_days < SNAPSHOT_MIN_AGE_DAYS:
                    continue

                old_snapshots.append({
                    'Region': region,
                    'SnapshotKind': 'Instance',
                    'SnapshotId': snap.get('DBSnapshotIdentifier', ''),
                    'SourceId': snap.get('DBInstanceIdentifier', ''),
                    'SnapshotType': snap.get('SnapshotType', ''),
                    'Engine': snap.get('Engine', ''),
                    'EngineVersion': snap.get('EngineVersion', ''),
                    'AllocatedStorageGb': snap.get('AllocatedStorage', ''),
                    'Encrypted': snap.get('Encrypted', False),
                    'Status': snap.get('Status', ''),
                    'SnapshotCreateTime': create_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'AgeInDays': age_days,
                    'SnapshotArn': snap.get('DBSnapshotArn', ''),
                })

        # Aurora / Multi-AZ cluster snapshots
        paginator = rds.get_paginator('describe_db_cluster_snapshots')
        for page in paginator.paginate():
            for snap in page.get('DBClusterSnapshots', []):
                create_time = snap.get('SnapshotCreateTime')
                if not create_time:
                    continue
                age_days = age_in_days(create_time)
                if age_days < SNAPSHOT_MIN_AGE_DAYS:
                    continue

                old_snapshots.append({
                    'Region': region,
                    'SnapshotKind': 'Cluster',
                    'SnapshotId': snap.get('DBClusterSnapshotIdentifier', ''),
                    'SourceId': snap.get('DBClusterIdentifier', ''),
                    'SnapshotType': snap.get('SnapshotType', ''),
                    'Engine': snap.get('Engine', ''),
                    'EngineVersion': snap.get('EngineVersion', ''),
                    'AllocatedStorageGb': snap.get('AllocatedStorage', ''),
                    'Encrypted': snap.get('StorageEncrypted', False),
                    'Status': snap.get('Status', ''),
                    'SnapshotCreateTime': create_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'AgeInDays': age_days,
                    'SnapshotArn': snap.get('DBClusterSnapshotArn', ''),
                })

        count = len([s for s in old_snapshots if s['Region'] == region])
        print(f"  RDS snapshots older than {SNAPSHOT_MIN_AGE_DAYS} days in {region}: {count}")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'rds_snapshots_older_than_{SNAPSHOT_MIN_AGE_DAYS}_days_{ts}.csv'

csv_columns = [
    'Region',
    'SnapshotKind',
    'SnapshotId',
    'SourceId',
    'SnapshotType',
    'Engine',
    'EngineVersion',
    'AllocatedStorageGb',
    'Encrypted',
    'Status',
    'SnapshotCreateTime',
    'AgeInDays',
    'SnapshotArn',
]

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=csv_columns)
    writer.writeheader()
    writer.writerows(old_snapshots)

manual = [s for s in old_snapshots if s['SnapshotType'] == 'manual']
total_gb = sum(s['AllocatedStorageGb'] for s in old_snapshots if isinstance(s['AllocatedStorageGb'], int))
unencrypted = [s for s in old_snapshots if not s['Encrypted']]

print(f"\nCSV exported: {csv_filename}")
print(f"Total RDS snapshots older than {SNAPSHOT_MIN_AGE_DAYS} days: {len(old_snapshots)} (manual: {len(manual)})")
print(f"Total allocated storage (Gb, source size): {total_gb}")
print(f"Unencrypted old snapshots: {len(unencrypted)}")
