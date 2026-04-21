"""
Per ECR repository: image count, tagged vs untagged counts, and sum of imageSizeInBytes
(approximate storage; shared layers may be counted per image in this sum).

Usage:
  python ecr/read-ecr-repository-summary.py
  python ecr/read-ecr-repository-summary.py sa-east-1
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

rows = []

for region in regions:
    print(f"Checking region: {region}")

    try:
        ecr = boto3.client('ecr', region_name=region)
        for page in ecr.get_paginator('describe_repositories').paginate():
            for repo in page.get('repositories', []):
                repo_name = repo['repositoryName']
                uri = repo.get('repositoryUri', '')
                created = repo.get('createdAt', '')
                if created:
                    created = created.strftime('%Y-%m-%d %H:%M:%S')

                scan = repo.get('imageScanningConfiguration', {}) or {}
                scan_on_push = scan.get('scanOnPush', False)

                image_count = 0
                tagged_count = 0
                untagged_count = 0
                total_size_bytes = 0

                for img_page in ecr.get_paginator('describe_images').paginate(repositoryName=repo_name):
                    for img in img_page.get('imageDetails', []):
                        image_count += 1
                        total_size_bytes += int(img.get('imageSizeInBytes') or 0)
                        if img.get('imageTags'):
                            tagged_count += 1
                        else:
                            untagged_count += 1

                rows.append({
                    'Region': region,
                    'RepositoryName': repo_name,
                    'RepositoryUri': uri,
                    'RepositoryCreatedAt': created,
                    'ScanOnPush': scan_on_push,
                    'ImageCount': image_count,
                    'TaggedImageCount': tagged_count,
                    'UntaggedImageCount': untagged_count,
                    'TotalImageSizeBytes': total_size_bytes,
                    'TotalImageSizeGb': round(total_size_bytes / (1024**3), 4) if total_size_bytes else 0,
                })

        n_repos = len([r for r in rows if r['Region'] == region])
        print(f"  Repositories in {region}: {n_repos}")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'ecr_repository_summary_{ts}.csv'

fieldnames = [
    'Region',
    'RepositoryName',
    'RepositoryUri',
    'RepositoryCreatedAt',
    'ScanOnPush',
    'ImageCount',
    'TaggedImageCount',
    'UntaggedImageCount',
    'TotalImageSizeBytes',
    'TotalImageSizeGb',
]

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)

print(f"\nCSV exported: {csv_filename}")
print(f"Total repositories: {len(rows)}")
print("Note: TotalImageSizeBytes sums per-image sizes; shared layers may double-count across images.")
