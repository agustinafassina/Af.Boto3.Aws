import boto3
import csv
import sys
from datetime import datetime

# List EBS snapshots owned by this account older than N days (default 90)
SNAPSHOT_MIN_AGE_DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 90

ec2 = boto3.client('ec2', region_name='us-east-1')
regions_response = ec2.describe_regions()
regions = [region['RegionName'] for region in regions_response['Regions']]

old_snapshots = []

for region in regions:
    print(f"Checking region: {region}")

    try:
        regional_ec2 = boto3.client('ec2', region_name=region)
        paginator = regional_ec2.get_paginator('describe_snapshots')
        for page in paginator.paginate(OwnerIds=['self']):
            for snap in page.get('Snapshots', []):
                start_time = snap.get('StartTime')
                if not start_time:
                    continue
                age_days = (datetime.now(start_time.tzinfo) - start_time).days
                if age_days < SNAPSHOT_MIN_AGE_DAYS:
                    continue

                tags = snap.get('Tags') or []
                tags_str = '; '.join(f"{t['Key']}={t['Value']}" for t in tags)

                old_snapshots.append({
                    'Region': region,
                    'SnapshotId': snap.get('SnapshotId', ''),
                    'VolumeId': snap.get('VolumeId', ''),
                    'VolumeSizeGb': snap.get('VolumeSize', ''),
                    'StartTime': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'AgeInDays': age_days,
                    'Description': (snap.get('Description') or '')[:200],
                    'Tags': tags_str,
                })

        count = len([s for s in old_snapshots if s['Region'] == region])
        print(f"  Snapshots older than {SNAPSHOT_MIN_AGE_DAYS} days in {region}: {count}")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'ebs_snapshots_older_than_{SNAPSHOT_MIN_AGE_DAYS}_days_{ts}.csv'

csv_columns = [
    'Region',
    'SnapshotId',
    'VolumeId',
    'VolumeSizeGb',
    'StartTime',
    'AgeInDays',
    'Description',
    'Tags',
]

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=csv_columns)
    writer.writeheader()
    writer.writerows(old_snapshots)

total_gb = sum(s['VolumeSizeGb'] for s in old_snapshots if isinstance(s['VolumeSizeGb'], int))
print(f"\nCSV exported: {csv_filename}")
print(f"Total snapshots older than {SNAPSHOT_MIN_AGE_DAYS} days: {len(old_snapshots)}")
print(f"Total snapshot size (Gb): {total_gb}")
