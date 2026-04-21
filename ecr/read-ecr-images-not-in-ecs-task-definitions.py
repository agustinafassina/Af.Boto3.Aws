"""
List ECR images (per repository) that are not referenced by any ACTIVE ECS task
definition container image string in the account.

Collects image URIs from all regions (ECS task definitions can reference any ECR URI).
Then scans ECR in each region (or one region if passed as argument).

Does not consider: INACTIVE task definitions (optional below), Lambda, CodeBuild,
Batch, Kubernetes outside ECS, or images only in stopped tasks. Review before delete.
"""
import boto3
import csv
import re
import sys
from datetime import datetime

# Set True to also scan INACTIVE task definitions (fewer false "unused", more API calls)
INCLUDE_INACTIVE_TASK_DEFINITIONS = False

filter_ecr_region = sys.argv[1] if len(sys.argv) > 1 else None

ec2 = boto3.client('ec2', region_name='us-east-1')
all_regions = [r['RegionName'] for r in ec2.describe_regions()['Regions']]
ecr_regions = [filter_ecr_region] if filter_ecr_region else all_regions

if filter_ecr_region and filter_ecr_region not in all_regions:
    print(f"Invalid ECR region: {filter_ecr_region}")
    sys.exit(1)

DIGEST_RE = re.compile(r"sha256:[a-f0-9]{64}")


def collect_images_from_task_definition(td):
    images = []
    for c in td.get('containerDefinitions') or []:
        img = (c.get('image') or '').strip()
        if img:
            images.append(img)
    return images


def collect_all_ecs_task_definition_images():
    """All container image strings from ACTIVE (and optionally INACTIVE) ECS task defs."""
    td_images = set()
    n_defs = 0

    for region in all_regions:
        print(f"Scanning ECS task definitions in: {region}")
        try:
            ecs = boto3.client('ecs', region_name=region)
            statuses = ['ACTIVE', 'INACTIVE'] if INCLUDE_INACTIVE_TASK_DEFINITIONS else ['ACTIVE']
            for status in statuses:
                for page in ecs.get_paginator('list_task_definitions').paginate(status=status):
                    for arn in page.get('taskDefinitionArns', []):
                        try:
                            resp = ecs.describe_task_definition(taskDefinition=arn)
                            td = resp.get('taskDefinition', {})
                            for img in collect_images_from_task_definition(td):
                                td_images.add(img)
                            n_defs += 1
                            if n_defs % 100 == 0:
                                print(f"  ... {n_defs} task definitions, {len(td_images)} unique image strings")
                        except Exception as e:
                            print(f"  describe_task_definition error {arn}: {e}")
        except Exception as e:
            print(f"Error in region {region}: {e}")
            continue

    print(f"Total task definitions scanned: {n_defs}, unique image strings: {len(td_images)}")
    return td_images


def is_ecr_image_referenced(registry, repository_name, digest, image_tags, td_images):
    """
    True if any task definition image string references this digest or repo:tag
    for this registry/repo.
    """
    tags = image_tags or []
    variants = [f"{registry}/{repository_name}@{digest}"]
    for tag in tags:
        variants.append(f"{registry}/{repository_name}:{tag}")

    for v in variants:
        if v in td_images:
            return True

    for td in td_images:
        if digest and digest in td:
            if repository_name not in td and repository_name.split('/')[-1] not in td:
                continue
            if registry in td or registry.replace('https://', '') in td:
                return True
            if '.dkr.ecr.' in td and digest in td:
                return True
        for tag in tags:
            if not tag:
                continue
            suffix = f"{repository_name}:{tag}"
            if td == suffix or td.endswith('/' + suffix) or td.endswith(suffix):
                return True
            if f":{tag}" in td and repository_name in td:
                return True

    for td in td_images:
        m = DIGEST_RE.search(td)
        if m and m.group(0) == digest and repository_name in td:
            return True

    return False


print("Step 1: Collecting image strings from ECS task definitions (all regions)...")
td_images = collect_all_ecs_task_definition_images()

sts = boto3.client('sts')
account_id = sts.get_caller_identity()['Account']

unused_rows = []

for region in ecr_regions:
    registry = f"{account_id}.dkr.ecr.{region}.amazonaws.com"
    print(f"\nStep 2: Scanning ECR in {region}")

    try:
        ecr = boto3.client('ecr', region_name=region)
        repos = []
        for page in ecr.get_paginator('describe_repositories').paginate():
            repos.extend(page.get('repositories', []))

        for repo in repos:
            repo_name = repo['repositoryName']
            paginator = ecr.get_paginator('describe_images')
            for page in paginator.paginate(repositoryName=repo_name):
                for img in page.get('imageDetails', []):
                    digest = img.get('imageDigest', '')
                    tags = img.get('imageTags') or []
                    pushed = img.get('imagePushedAt', '')
                    if pushed:
                        pushed = pushed.strftime('%Y-%m-%d %H:%M:%S')

                    if is_ecr_image_referenced(registry, repo_name, digest, tags, td_images):
                        continue

                    unused_rows.append({
                        'Region': region,
                        'Registry': registry,
                        'RepositoryName': repo_name,
                        'ImageDigest': digest,
                        'ImageTags': ','.join(tags) if tags else '(untagged)',
                        'ImagePushedAt': pushed,
                    })

        n_unused = len([r for r in unused_rows if r['Region'] == region])
        print(f"  Unused images in {region}: {n_unused}")

    except Exception as e:
        print(f"Error scanning ECR in {region}: {e}")
        continue

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'ecr_images_not_in_ecs_task_definitions_{ts}.csv'

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(
        f,
        fieldnames=['Region', 'Registry', 'RepositoryName', 'ImageDigest', 'ImageTags', 'ImagePushedAt'],
    )
    w.writeheader()
    w.writerows(unused_rows)

print(f"\nCSV exported: {csv_filename}")
print(f"Total ECR images not matched to any ECS task definition image string: {len(unused_rows)}")
print("Review before deleting images (lifecycle policy or batch-delete).")
