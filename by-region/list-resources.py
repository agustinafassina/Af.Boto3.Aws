import boto3
import csv
from collections import Counter
from datetime import datetime

REGION = 'sa-east-1'

# Rows: Service, ResourceType, ResourceId, Name, Extra
rows = []


def add(service, resource_type, resource_id, name='', extra=''):
    rows.append({
        'Region': REGION,
        'Service': service,
        'ResourceType': resource_type,
        'ResourceId': resource_id,
        'Name': name or resource_id,
        'Extra': str(extra)[:200] if extra else '',
    })

print(f"Listing resources in region: {REGION}")

# EC2 - Instances
try:
    ec2 = boto3.client('ec2', region_name=REGION)
    for page in ec2.get_paginator('describe_instances').paginate():
        for res in page.get('Reservations', []):
            for inst in res.get('Instances', []):
                name = next((t['Value'] for t in (inst.get('Tags') or []) if t['Key'] == 'Name'), '') or inst.get('InstanceId', '')
                add('ec2', 'instance', inst.get('InstanceId', ''), name, inst.get('State', {}).get('Name', ''))
except Exception as e:
    add('ec2', 'instance', 'error', '', str(e))

# EC2 - Volumes
try:
    ec2 = boto3.client('ec2', region_name=REGION)
    for page in ec2.get_paginator('describe_volumes').paginate():
        for vol in page.get('Volumes', []):
            name = next((t['Value'] for t in (vol.get('Tags') or []) if t['Key'] == 'Name'), '') or vol.get('VolumeId', '')
            add('ec2', 'volume', vol.get('VolumeId', ''), name, f"{vol.get('Size')} GiB, {vol.get('State', '')}")
except Exception as e:
    add('ec2', 'volume', 'error', '', str(e))

# EC2 - Security groups
try:
    ec2 = boto3.client('ec2', region_name=REGION)
    for page in ec2.get_paginator('describe_security_groups').paginate():
        for sg in page.get('SecurityGroups', []):
            add('ec2', 'security-group', sg.get('GroupId', ''), sg.get('GroupName', ''), sg.get('VpcId', ''))
except Exception as e:
    add('ec2', 'security-group', 'error', '', str(e))

# EC2 - VPCs
try:
    ec2 = boto3.client('ec2', region_name=REGION)
    for vpc in ec2.describe_vpcs().get('Vpcs', []):
        name = next((t['Value'] for t in (vpc.get('Tags') or []) if t['Key'] == 'Name'), '') or vpc.get('VpcId', '')
        add('ec2', 'vpc', vpc.get('VpcId', ''), name, vpc.get('CidrBlock', ''))
except Exception as e:
    add('ec2', 'vpc', 'error', '', str(e))

# EC2 - AMIs (owned by account)
try:
    ec2 = boto3.client('ec2', region_name=REGION)
    for page in ec2.get_paginator('describe_images').paginate(Owners=['self']):
        for img in page.get('Images', []):
            add('ec2', 'ami', img.get('ImageId', ''), img.get('Name', ''), img.get('State', ''))
except Exception as e:
    add('ec2', 'ami', 'error', '', str(e))

# EC2 - Snapshots (owned by account)
try:
    ec2 = boto3.client('ec2', region_name=REGION)
    for page in ec2.get_paginator('describe_snapshots').paginate(OwnerIds=['self']):
        for snap in page.get('Snapshots', []):
            add('ec2', 'snapshot', snap.get('SnapshotId', ''), snap.get('SnapshotId', ''), f"{snap.get('VolumeSize')} GiB")
except Exception as e:
    add('ec2', 'snapshot', 'error', '', str(e))

# RDS
try:
    rds = boto3.client('rds', region_name=REGION)
    for page in rds.get_paginator('describe_db_instances').paginate():
        for db in page.get('DBInstances', []):
            add('rds', 'db-instance', db.get('DBInstanceIdentifier', ''), db.get('DBInstanceIdentifier', ''), db.get('Engine', ''))
except Exception as e:
    add('rds', 'db-instance', 'error', '', str(e))

# Lambda
try:
    lam = boto3.client('lambda', region_name=REGION)
    for page in lam.get_paginator('list_functions').paginate():
        for fn in page.get('Functions', []):
            add('lambda', 'function', fn.get('FunctionName', ''), fn.get('FunctionName', ''), fn.get('Runtime', ''))
except Exception as e:
    add('lambda', 'function', 'error', '', str(e))

# ECR repositories
try:
    ecr = boto3.client('ecr', region_name=REGION)
    for page in ecr.get_paginator('describe_repositories').paginate():
        for repo in page.get('repositories', []):
            add('ecr', 'repository', repo.get('repositoryName', ''), repo.get('repositoryName', ''), '')
except Exception as e:
    add('ecr', 'repository', 'error', '', str(e))

# S3 buckets (global, but we include those in this region)
try:
    s3 = boto3.client('s3')
    for b in s3.list_buckets().get('Buckets', []):
        try:
            loc = s3.get_bucket_location(Bucket=b['Name']).get('LocationConstraint') or 'us-east-1'
            if loc == REGION:
                add('s3', 'bucket', b['Name'], b['Name'], loc)
        except Exception:
            pass
except Exception as e:
    add('s3', 'bucket', 'error', '', str(e))

# CloudWatch Log Groups
try:
    logs = boto3.client('logs', region_name=REGION)
    for page in logs.get_paginator('describe_log_groups').paginate():
        for lg in page.get('logGroups', []):
            add('logs', 'log-group', lg.get('logGroupName', ''), lg.get('logGroupName', ''), '')
except Exception as e:
    add('logs', 'log-group', 'error', '', str(e))

# Export CSV
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'resources_{REGION}_{ts}.csv'

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['Region', 'Service', 'ResourceType', 'ResourceId', 'Name', 'Extra'])
    w.writeheader()
    w.writerows(rows)

# Remove error placeholder rows for count
data_rows = [r for r in rows if r['ResourceId'] != 'error']
print(f"\nCSV exported: {csv_filename}")
print(f"Region: {REGION} (Stockholm)")
print(f"Total resources: {len(data_rows)}")

# Summary by type
by_type = Counter((r['Service'], r['ResourceType']) for r in data_rows)
for (svc, rtype), count in sorted(by_type.items(), key=lambda x: (-x[1], x[0])):
    print(f"  {svc} / {rtype}: {count}")
