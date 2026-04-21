"""
List ECS task definition revisions (ACTIVE) that are not referenced by any service
deployment or by any RUNNING task in the same region.

Does not detect: EventBridge scheduled tasks, Step Functions, manual RunTask that already
finished, or other accounts. Use the CSV as a guide before deregistering.
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


def task_def_key(arn_or_id):
    """Normalize to 'family:revision' for comparison."""
    if not arn_or_id:
        return ''
    s = str(arn_or_id).strip()
    if '/' in s:
        s = s.rsplit('/', 1)[-1]
    return s


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def collect_in_use_task_definitions(ecs, cluster_arn):
    """Task definition ARNs (as family:revision keys) in use by this cluster."""
    used = set()

    service_arns = []
    sp = ecs.get_paginator('list_services')
    for page in sp.paginate(cluster=cluster_arn):
        service_arns.extend(page.get('serviceArns', []))

    for svc_chunk in chunks(service_arns, 10):
        resp = ecs.describe_services(cluster=cluster_arn, services=svc_chunk)
        for svc in resp.get('services', []):
            used.add(task_def_key(svc.get('taskDefinition', '')))
            for dep in svc.get('deployments', []) or []:
                td = dep.get('taskDefinition')
                if td:
                    used.add(task_def_key(td))

    task_arns = []
    tp = ecs.get_paginator('list_tasks')
    for page in tp.paginate(cluster=cluster_arn, desiredStatus='RUNNING'):
        task_arns.extend(page.get('taskArns', []))

    for task_chunk in chunks(task_arns, 100):
        tresp = ecs.describe_tasks(cluster=cluster_arn, tasks=task_chunk)
        for task in tresp.get('tasks', []):
            used.add(task_def_key(task.get('taskDefinitionArn', '')))

    used.discard('')
    return used


unused_rows = []
stats_by_region = []

for region in regions:
    print(f"Checking region: {region}")

    try:
        ecs = boto3.client('ecs', region_name=region)

        cluster_arns = []
        for page in ecs.get_paginator('list_clusters').paginate():
            cluster_arns.extend(page.get('clusterArns', []))

        in_use = set()
        for arn in cluster_arns:
            in_use |= collect_in_use_task_definitions(ecs, arn)

        all_active_arns = []
        for page in ecs.get_paginator('list_task_definitions').paginate(status='ACTIVE'):
            all_active_arns.extend(page.get('taskDefinitionArns', []))

        total_active = len(all_active_arns)
        unused_in_region = 0
        for td_arn in all_active_arns:
            key = task_def_key(td_arn)
            if key in in_use:
                continue
            family, _, revision = key.rpartition(':')
            if not revision.isdigit():
                family = key
                revision = ''
            unused_rows.append({
                'Region': region,
                'TaskDefinitionFamily': family,
                'Revision': revision,
                'TaskDefinitionArn': td_arn,
            })
            unused_in_region += 1

        stats_by_region.append((region, total_active, len(in_use), unused_in_region))
        print(f"  ACTIVE task definitions: {total_active}, in use (unique): {len(in_use)}, unused: {unused_in_region}")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'ecs_unused_task_definitions_{ts}.csv'

csv_columns = ['Region', 'TaskDefinitionFamily', 'Revision', 'TaskDefinitionArn']

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=csv_columns)
    w.writeheader()
    w.writerows(unused_rows)

print(f"\nCSV exported: {csv_filename}")
print(f"Total unused ACTIVE task definition revisions: {len(unused_rows)}")
for region, total_active_ct, in_use_ct, unused_ct in stats_by_region:
    print(f"  {region}: unused {unused_ct} / ACTIVE total {total_active_ct} (unique in use: {in_use_ct})")
