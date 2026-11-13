import boto3
import csv
import sys
from datetime import datetime

# Audit RDS instances for automated backups and storage encryption.
# - BackupRetentionPeriod = 0 means automated backups are disabled.
# - For Aurora members, retention and encryption come from the cluster.
# Exports every instance with flags; prints the ones that need review.
# Usage:
#   python rds/read-rds-backup-encryption-audit.py
#   python rds/read-rds-backup-encryption-audit.py sa-east-1
filter_region = sys.argv[1] if len(sys.argv) > 1 else None

ec2 = boto3.client('ec2', region_name='us-east-1')
all_regions = [r['RegionName'] for r in ec2.describe_regions()['Regions']]

if filter_region and filter_region not in all_regions:
    print(f"Invalid region: {filter_region}")
    sys.exit(1)

regions = [filter_region] if filter_region else all_regions

audit_data = []

for region in regions:
    print(f"Checking region: {region}")

    try:
        rds = boto3.client('rds', region_name=region)

        clusters = {}
        for page in rds.get_paginator('describe_db_clusters').paginate():
            for cluster in page.get('DBClusters', []):
                clusters[cluster['DBClusterIdentifier']] = cluster

        for page in rds.get_paginator('describe_db_instances').paginate():
            for db in page.get('DBInstances', []):
                cluster_id = db.get('DBClusterIdentifier', '')
                cluster = clusters.get(cluster_id) if cluster_id else None

                if cluster:
                    retention = cluster.get('BackupRetentionPeriod', 0)
                    encrypted = cluster.get('StorageEncrypted', False)
                    kms_key = cluster.get('KmsKeyId', '')
                    deletion_protection = cluster.get('DeletionProtection', False)
                else:
                    retention = db.get('BackupRetentionPeriod', 0)
                    encrypted = db.get('StorageEncrypted', False)
                    kms_key = db.get('KmsKeyId', '')
                    deletion_protection = db.get('DeletionProtection', False)

                backups_enabled = retention > 0
                findings = []
                if not backups_enabled:
                    findings.append('NoAutomatedBackups')
                if not encrypted:
                    findings.append('NotEncrypted')

                audit_data.append({
                    'Region': region,
                    'DBInstanceIdentifier': db.get('DBInstanceIdentifier', ''),
                    'DBClusterIdentifier': cluster_id,
                    'Engine': db.get('Engine', ''),
                    'EngineVersion': db.get('EngineVersion', ''),
                    'DBInstanceClass': db.get('DBInstanceClass', ''),
                    'DBInstanceStatus': db.get('DBInstanceStatus', ''),
                    'BackupRetentionPeriod': retention,
                    'BackupsEnabled': 'Yes' if backups_enabled else 'No',
                    'PreferredBackupWindow': (cluster or db).get('PreferredBackupWindow', ''),
                    'StorageEncrypted': 'Yes' if encrypted else 'No',
                    'KmsKeyId': kms_key,
                    'DeletionProtection': 'Yes' if deletion_protection else 'No',
                    'Findings': '; '.join(findings),
                    'DBInstanceArn': db.get('DBInstanceArn', ''),
                })

        count = len([r for r in audit_data if r['Region'] == region])
        print(f"  RDS instances in {region}: {count}")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

if not audit_data:
    print("\nNo RDS instances found.")
    sys.exit(0)

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'rds_backup_encryption_audit_{ts}.csv'

csv_columns = [
    'Region',
    'DBInstanceIdentifier',
    'DBClusterIdentifier',
    'Engine',
    'EngineVersion',
    'DBInstanceClass',
    'DBInstanceStatus',
    'BackupRetentionPeriod',
    'BackupsEnabled',
    'PreferredBackupWindow',
    'StorageEncrypted',
    'KmsKeyId',
    'DeletionProtection',
    'Findings',
    'DBInstanceArn',
]

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=csv_columns)
    writer.writeheader()
    writer.writerows(audit_data)

no_backups = [r for r in audit_data if r['BackupsEnabled'] == 'No']
not_encrypted = [r for r in audit_data if r['StorageEncrypted'] == 'No']

print(f"\nCSV exported: {csv_filename}")
print(f"Total RDS instances: {len(audit_data)}")
print(f"Without automated backups: {len(no_backups)}")
print(f"Without storage encryption: {len(not_encrypted)}")

flagged = [r for r in audit_data if r['Findings']]
if flagged:
    print("\nInstances that need review:")
    for r in flagged:
        print(f"  [{r['Region']}] {r['DBInstanceIdentifier']}: {r['Findings']}")
