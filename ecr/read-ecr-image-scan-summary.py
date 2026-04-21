"""
Summarize ECR basic image scan results: one row per image with scan status
and findingSeverityCounts (requires scan-on-push / completed scan).

Does not export every CVE line-by-line (counts only). Many API calls if many images.

Usage:
  python ecr/read-ecr-image-scan-summary.py
  python ecr/read-ecr-image-scan-summary.py sa-east-1
"""
import boto3
import csv
import sys
from datetime import datetime

from botocore.exceptions import ClientError

filter_region = sys.argv[1] if len(sys.argv) > 1 else None

ec2 = boto3.client('ec2', region_name='us-east-1')
all_regions = [r['RegionName'] for r in ec2.describe_regions()['Regions']]
regions = [filter_region] if filter_region else all_regions

if filter_region and filter_region not in all_regions:
    print(f"Invalid region: {filter_region}")
    sys.exit(1)

SEVERITY_KEYS = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL', 'UNDEFINED']


rows = []

for region in regions:
    print(f"Checking region: {region}")

    try:
        ecr = boto3.client('ecr', region_name=region)
        for page in ecr.get_paginator('describe_repositories').paginate():
            for repo in page.get('repositories', []):
                repo_name = repo['repositoryName']
                for img_page in ecr.get_paginator('describe_images').paginate(repositoryName=repo_name):
                    for img in img_page.get('imageDetails', []):
                        digest = img.get('imageDigest', '')
                        tags = img.get('imageTags') or []
                        iss = img.get('imageScanStatus') or {}
                        scan_status = iss.get('status', '') if isinstance(iss, dict) else str(iss)
                        if scan_status != 'COMPLETE':
                            rows.append(
                                {
                                    'Region': region,
                                    'RepositoryName': repo_name,
                                    'ImageDigest': digest,
                                    'ImageTags': ','.join(tags) if tags else '(untagged)',
                                    'ScanStatus': scan_status or 'UNKNOWN',
                                    'ImageScanCompletedAt': '',
                                    'CRITICAL': '',
                                    'HIGH': '',
                                    'MEDIUM': '',
                                    'LOW': '',
                                    'INFORMATIONAL': '',
                                    'UNDEFINED': '',
                                }
                            )
                            continue

                        try:
                            resp = ecr.describe_image_scan_findings(
                                repositoryName=repo_name,
                                imageId={'imageDigest': digest},
                                maxResults=1,
                            )
                        except ClientError as ce:
                            code = ce.response.get('Error', {}).get('Code', '')
                            if code == 'ScanNotFoundException':
                                rows.append(
                                    {
                                        'Region': region,
                                        'RepositoryName': repo_name,
                                        'ImageDigest': digest,
                                        'ImageTags': ','.join(tags) if tags else '(untagged)',
                                        'ScanStatus': 'NO_SCAN_FINDINGS',
                                        'ImageScanCompletedAt': '',
                                        'CRITICAL': '',
                                        'HIGH': '',
                                        'MEDIUM': '',
                                        'LOW': '',
                                        'INFORMATIONAL': '',
                                        'UNDEFINED': '',
                                    }
                                )
                            else:
                                rows.append(
                                    {
                                        'Region': region,
                                        'RepositoryName': repo_name,
                                        'ImageDigest': digest,
                                        'ImageTags': ','.join(tags) if tags else '(untagged)',
                                        'ScanStatus': f'error:{code}',
                                        'ImageScanCompletedAt': '',
                                        'CRITICAL': '',
                                        'HIGH': '',
                                        'MEDIUM': '',
                                        'LOW': '',
                                        'INFORMATIONAL': '',
                                        'UNDEFINED': '',
                                    }
                                )
                            continue
                        except Exception as e:
                            rows.append(
                                {
                                    'Region': region,
                                    'RepositoryName': repo_name,
                                    'ImageDigest': digest,
                                    'ImageTags': ','.join(tags) if tags else '(untagged)',
                                    'ScanStatus': f'error:{e}',
                                    'ImageScanCompletedAt': '',
                                    'CRITICAL': '',
                                    'HIGH': '',
                                    'MEDIUM': '',
                                    'LOW': '',
                                    'INFORMATIONAL': '',
                                    'UNDEFINED': '',
                                }
                            )
                            continue

                        completed = resp.get('imageScanCompletedAt', '')
                        if completed:
                            completed = completed.strftime('%Y-%m-%d %H:%M:%S')
                        counts = resp.get('findingSeverityCounts') or {}

                        row = {
                            'Region': region,
                            'RepositoryName': repo_name,
                            'ImageDigest': digest,
                            'ImageTags': ','.join(tags) if tags else '(untagged)',
                            'ScanStatus': scan_status,
                            'ImageScanCompletedAt': completed,
                        }
                        for k in SEVERITY_KEYS:
                            row[k] = counts.get(k, 0)
                        rows.append(row)

                        if counts.get('CRITICAL', 0) or counts.get('HIGH', 0):
                            print(
                                f"  {repo_name} {digest[:19]}... CRITICAL={counts.get('CRITICAL', 0)} HIGH={counts.get('HIGH', 0)}"
                            )

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'ecr_image_scan_summary_{ts}.csv'

fieldnames = [
    'Region',
    'RepositoryName',
    'ImageDigest',
    'ImageTags',
    'ScanStatus',
    'ImageScanCompletedAt',
] + SEVERITY_KEYS

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)

print(f"\nCSV exported: {csv_filename}")
print(f"Total image rows: {len(rows)}")
print("Rows with ScanStatus not COMPLETE may have no scan yet or scanning failed.")
