import boto3
import csv
from datetime import datetime

s3 = boto3.client('s3')


def get_bucket_region(bucket_name):
    try:
        response = s3.get_bucket_location(Bucket=bucket_name)
        region = response.get('LocationConstraint')
        if region is None:
            return 'us-east-1'
        return region
    except Exception as e:
        print(f"Error getting region for {bucket_name}: {e}")
        return 'Unknown'


def get_public_access_block(bucket_name):
    try:
        response = s3.get_public_access_block(Bucket=bucket_name)
        cfg = response.get('PublicAccessBlockConfiguration', {})
        return {
            'BlockPublicAcls': cfg.get('BlockPublicAcls', False),
            'IgnorePublicAcls': cfg.get('IgnorePublicAcls', False),
            'BlockPublicPolicy': cfg.get('BlockPublicPolicy', False),
            'RestrictPublicBuckets': cfg.get('RestrictPublicBuckets', False),
            'PublicAccessBlockStatus': 'configured',
        }
    except s3.exceptions.ClientError as e:
        code = e.response['Error']['Code']
        if code in ('NoSuchPublicAccessBlock', 'NoSuchPublicAccessBlockConfiguration'):
            return {
                'BlockPublicAcls': '',
                'IgnorePublicAcls': '',
                'BlockPublicPolicy': '',
                'RestrictPublicBuckets': '',
                'PublicAccessBlockStatus': 'not_configured',
            }
        return {
            'BlockPublicAcls': '',
            'IgnorePublicAcls': '',
            'BlockPublicPolicy': '',
            'RestrictPublicBuckets': '',
            'PublicAccessBlockStatus': f'error:{code}',
        }


def is_fully_blocked(row):
    if row['PublicAccessBlockStatus'] != 'configured':
        return False
    return all(
        row[k] is True
        for k in ('BlockPublicAcls', 'IgnorePublicAcls', 'BlockPublicPolicy', 'RestrictPublicBuckets')
    )


rows = []

print('Listing S3 buckets and public access block...')

for bucket in s3.list_buckets().get('Buckets', []):
    name = bucket['Name']
    region = get_bucket_region(name)
    block = get_public_access_block(name)

    row = {
        'BucketName': name,
        'Region': region,
        'BlockPublicAcls': block['BlockPublicAcls'],
        'IgnorePublicAcls': block['IgnorePublicAcls'],
        'BlockPublicPolicy': block['BlockPublicPolicy'],
        'RestrictPublicBuckets': block['RestrictPublicBuckets'],
        'PublicAccessBlockStatus': block['PublicAccessBlockStatus'],
    }
    row['FullyBlocked'] = 'Yes' if is_fully_blocked(row) else 'No'
    rows.append(row)
    if row['FullyBlocked'] == 'No':
        print(f"  Review: {name} ({region}) — FullyBlocked={row['FullyBlocked']}, status={row['PublicAccessBlockStatus']}")

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f's3_public_access_block_{ts}.csv'

csv_columns = [
    'BucketName',
    'Region',
    'BlockPublicAcls',
    'IgnorePublicAcls',
    'BlockPublicPolicy',
    'RestrictPublicBuckets',
    'PublicAccessBlockStatus',
    'FullyBlocked',
]

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=csv_columns)
    writer.writeheader()
    writer.writerows(rows)

not_fully = sum(1 for r in rows if r['FullyBlocked'] == 'No')
print(f"\nCSV exported: {csv_filename}")
print(f"Total buckets: {len(rows)}")
print(f"Buckets not fully blocked (review): {not_fully}")
