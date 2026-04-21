"""
List ECR images that have no tags (digest-only / untagged).
Optionally restrict to images pushed more than N days ago (default: list all untagged).

Usage:
  python ecr/read-ecr-untagged-images.py
  python ecr/read-ecr-untagged-images.py sa-east-1
  python ecr/read-ecr-untagged-images.py sa-east-1 30
"""
import boto3
import csv
import sys
from datetime import datetime, timezone

filter_region = sys.argv[1] if len(sys.argv) > 1 else None
min_age_days = int(sys.argv[2]) if len(sys.argv) > 2 else 0

ec2 = boto3.client('ec2', region_name='us-east-1')
all_regions = [r['RegionName'] for r in ec2.describe_regions()['Regions']]
regions = [filter_region] if filter_region else all_regions

if filter_region and filter_region not in all_regions:
    print(f"Invalid region: {filter_region}")
    sys.exit(1)


def utc_now():
    return datetime.now(timezone.utc)


rows = []

for region in regions:
    print(f"Checking region: {region}")

    try:
        ecr = boto3.client('ecr', region_name=region)
        repos = []
        for page in ecr.get_paginator('describe_repositories').paginate():
            repos.extend(page.get('repositories', []))

        for repo in repos:
            repo_name = repo['repositoryName']
            for page in ecr.get_paginator('describe_images').paginate(repositoryName=repo_name):
                for img in page.get('imageDetails', []):
                    tags = img.get('imageTags')
                    if tags:
                        continue

                    pushed = img.get('imagePushedAt')
                    age_days = ''
                    if min_age_days > 0 and not pushed:
                        continue
                    if pushed:
                        if pushed.tzinfo is None:
                            pushed = pushed.replace(tzinfo=timezone.utc)
                        age_days = (utc_now() - pushed).days
                        if min_age_days > 0 and age_days < min_age_days:
                            continue
                        pushed_str = pushed.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        pushed_str = ''

                    rows.append({
                        'Region': region,
                        'RepositoryName': repo_name,
                        'ImageDigest': img.get('imageDigest', ''),
                        'ImagePushedAt': pushed_str,
                        'AgeInDays': age_days if age_days != '' else '',
                        'ImageSizeInBytes': img.get('imageSizeInBytes', ''),
                    })

        n = len([r for r in rows if r['Region'] == region])
        print(f"  Untagged images in {region}: {n}")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'ecr_untagged_images_{ts}.csv'

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(
        f,
        fieldnames=[
            'Region',
            'RepositoryName',
            'ImageDigest',
            'ImagePushedAt',
            'AgeInDays',
            'ImageSizeInBytes',
        ],
    )
    w.writeheader()
    w.writerows(rows)

print(f"\nCSV exported: {csv_filename}")
print(f"Total untagged images: {len(rows)}")
if min_age_days > 0:
    print(f"(Only images at least {min_age_days} days old since push)")
