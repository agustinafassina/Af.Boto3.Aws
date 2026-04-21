"""
ECS inventory: clusters, services, and running tasks across all regions (or one region).
Exports three CSV files with the same timestamp.
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

clusters_rows = []
services_rows = []
tasks_rows = []

ts = datetime.now().strftime('%Y%m%d_%H%M%S')


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


for region in regions:
    print(f"Checking region: {region}")

    try:
        ecs = boto3.client('ecs', region_name=region)

        cluster_arns = []
        paginator = ecs.get_paginator('list_clusters')
        for page in paginator.paginate():
            cluster_arns.extend(page.get('clusterArns', []))

        if not cluster_arns:
            print(f"  No ECS clusters in {region}")
            continue

        for chunk in chunks(cluster_arns, 100):
            desc = ecs.describe_clusters(clusters=chunk).get('clusters', [])
            for c in desc:
                clusters_rows.append({
                    'Region': region,
                    'ClusterArn': c.get('clusterArn', ''),
                    'ClusterName': c.get('clusterName', ''),
                    'Status': c.get('status', ''),
                    'RunningTasksCount': c.get('runningTasksCount', ''),
                    'PendingTasksCount': c.get('pendingTasksCount', ''),
                    'ActiveServicesCount': c.get('activeServicesCount', ''),
                    'RegisteredContainerInstancesCount': c.get('registeredContainerInstancesCount', ''),
                })

        for cluster_arn in cluster_arns:
            cluster_name = cluster_arn.split('/')[-1]

            service_arns = []
            sp = ecs.get_paginator('list_services')
            for page in sp.paginate(cluster=cluster_arn):
                service_arns.extend(page.get('serviceArns', []))

            for svc_chunk in chunks(service_arns, 10):
                resp = ecs.describe_services(cluster=cluster_arn, services=svc_chunk)
                for svc in resp.get('services', []):
                    deployment_cfg = svc.get('deploymentConfiguration', {}) or {}
                    services_rows.append({
                        'Region': region,
                        'ClusterName': cluster_name,
                        'ServiceName': svc.get('serviceName', ''),
                        'ServiceArn': svc.get('serviceArn', ''),
                        'DesiredCount': svc.get('desiredCount', ''),
                        'RunningCount': svc.get('runningCount', ''),
                        'PendingCount': svc.get('pendingCount', ''),
                        'TaskDefinition': svc.get('taskDefinition', ''),
                        'LaunchType': svc.get('launchType', '') or 'UNKNOWN',
                        'SchedulingStrategy': svc.get('schedulingStrategy', ''),
                        'PlatformVersion': svc.get('platformVersion', ''),
                        'PlatformFamily': svc.get('platformFamily', ''),
                        'Status': svc.get('status', ''),
                        'DeploymentsMinHealthyPercent': deployment_cfg.get('minimumHealthyPercent', ''),
                        'DeploymentsMaxPercent': deployment_cfg.get('maximumPercent', ''),
                    })

            task_arns = []
            tp = ecs.get_paginator('list_tasks')
            for page in tp.paginate(cluster=cluster_arn, desiredStatus='RUNNING'):
                task_arns.extend(page.get('taskArns', []))

            for task_chunk in chunks(task_arns, 100):
                tresp = ecs.describe_tasks(cluster=cluster_arn, tasks=task_chunk)
                for task in tresp.get('tasks', []):
                    images = []
                    for c in task.get('containers', []):
                        nm = c.get('name', '')
                        img = c.get('image', '')
                        images.append(f"{nm}={img}" if nm else img)
                    images_str = ' | '.join(images)[:800]

                    started = task.get('startedAt', '')
                    if started:
                        started = started.strftime('%Y-%m-%d %H:%M:%S')

                    tasks_rows.append({
                        'Region': region,
                        'ClusterName': cluster_name,
                        'Group': task.get('group', ''),
                        'TaskArn': task.get('taskArn', ''),
                        'LastStatus': task.get('lastStatus', ''),
                        'DesiredStatus': task.get('desiredStatus', ''),
                        'TaskDefinitionArn': task.get('taskDefinitionArn', ''),
                        'StartedAt': started,
                        'Cpu': task.get('cpu', ''),
                        'Memory': task.get('memory', ''),
                        'ContainersImages': images_str,
                    })

        print(
            f"  ECS in {region}: {len([c for c in clusters_rows if c['Region']==region])} clusters, "
            f"{len([s for s in services_rows if s['Region']==region])} services, "
            f"{len([t for t in tasks_rows if t['Region']==region])} running tasks"
        )

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue


def write_csv(filename, fieldnames, data):
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(data)
    print(f"  Wrote {filename} ({len(data)} rows)")


clusters_file = f'ecs_clusters_{ts}.csv'
services_file = f'ecs_services_{ts}.csv'
tasks_file = f'ecs_running_tasks_{ts}.csv'

write_csv(
    clusters_file,
    [
        'Region',
        'ClusterArn',
        'ClusterName',
        'Status',
        'RunningTasksCount',
        'PendingTasksCount',
        'ActiveServicesCount',
        'RegisteredContainerInstancesCount',
    ],
    clusters_rows,
)

write_csv(
    services_file,
    [
        'Region',
        'ClusterName',
        'ServiceName',
        'ServiceArn',
        'DesiredCount',
        'RunningCount',
        'PendingCount',
        'TaskDefinition',
        'LaunchType',
        'SchedulingStrategy',
        'PlatformVersion',
        'PlatformFamily',
        'Status',
        'DeploymentsMinHealthyPercent',
        'DeploymentsMaxPercent',
    ],
    services_rows,
)

write_csv(
    tasks_file,
    [
        'Region',
        'ClusterName',
        'Group',
        'TaskArn',
        'LastStatus',
        'DesiredStatus',
        'TaskDefinitionArn',
        'StartedAt',
        'Cpu',
        'Memory',
        'ContainersImages',
    ],
    tasks_rows,
)

print(f"\nDone. Timestamp: {ts}")
