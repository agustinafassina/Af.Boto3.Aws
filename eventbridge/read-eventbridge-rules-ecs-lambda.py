import boto3
import csv
import json
import sys
from datetime import datetime

TARGET_TYPES = {'ecs', 'lambda'}

filter_region = sys.argv[1] if len(sys.argv) > 1 else None

ec2 = boto3.client('ec2', region_name='us-east-1')
all_regions = [r['RegionName'] for r in ec2.describe_regions()['Regions']]
regions = [filter_region] if filter_region else all_regions

if filter_region and filter_region not in all_regions:
    print(f"Invalid region: {filter_region}")
    sys.exit(1)


def target_type_from_arn(arn):
    if not arn:
        return ''
    parts = arn.split(':')
    if len(parts) < 3:
        return ''
    service = parts[2]
    if service == 'ecs':
        return 'ecs'
    if service == 'lambda':
        return 'lambda'
    return service


def list_event_buses(events):
    buses = ['default']
    try:
        for page in events.get_paginator('list_event_buses').paginate():
            for bus in page.get('EventBuses', []):
                name = bus.get('Name', '')
                if name and name not in buses:
                    buses.append(name)
    except Exception as e:
        print(f"  list_event_buses warning: {e}")
    return buses


def list_all_targets(events, rule_name, bus_name):
    targets = []
    next_token = None
    while True:
        kwargs = {'Rule': rule_name, 'EventBusName': bus_name}
        if next_token:
            kwargs['NextToken'] = next_token
        resp = events.list_targets_by_rule(**kwargs)
        targets.extend(resp.get('Targets', []))
        next_token = resp.get('NextToken')
        if not next_token:
            break
    return targets


def ecs_details(target):
    """Extract RunTask / ECS parameters when present on an EventBridge target."""
    ecs = target.get('EcsParameters') or {}
    if not ecs:
        return '', '', '', ''
    cluster = ecs.get('ClusterArn') or ecs.get('Cluster', '')
    task_def = ecs.get('TaskDefinitionArn', '')
    launch = ecs.get('LaunchType', '')
    count = ecs.get('TaskCount', '')
    return cluster, task_def, launch, count


rows = []

for region in regions:
    print(f"Checking region: {region}")

    try:
        events = boto3.client('events', region_name=region)
        buses = list_event_buses(events)
        matched = 0

        for bus_name in buses:
            try:
                for page in events.get_paginator('list_rules').paginate(EventBusName=bus_name):
                    for rule in page.get('Rules', []):
                        rule_name = rule.get('Name', '')
                        schedule = rule.get('ScheduleExpression', '')
                        pattern = rule.get('EventPattern', '')
                        if pattern and len(pattern) > 500:
                            pattern = pattern[:500] + '...'

                        try:
                            targets = list_all_targets(events, rule_name, bus_name)
                        except Exception as te:
                            print(f"  list_targets_by_rule {rule_name}: {te}")
                            continue

                        for t in targets:
                            t_arn = t.get('Arn', '')
                            t_type = target_type_from_arn(t_arn)
                            if t_type not in TARGET_TYPES:
                                continue

                            cluster, task_def, launch, task_count = ecs_details(t)

                            t_input = t.get('Input') or t.get('InputPath') or ''
                            if t.get('InputTransformer'):
                                t_input = json.dumps(
                                    t.get('InputTransformer'),
                                    separators=(',', ':'),
                                )[:300]
                            elif isinstance(t_input, str) and len(t_input) > 300:
                                t_input = t_input[:300] + '...'

                            rows.append(
                                {
                                    'Region': region,
                                    'EventBusName': bus_name,
                                    'RuleName': rule_name,
                                    'RuleArn': rule.get('Arn', ''),
                                    'State': rule.get('State', ''),
                                    'Description': (rule.get('Description') or '')[:200],
                                    'ScheduleExpression': schedule,
                                    'EventPattern': pattern,
                                    'ManagedBy': rule.get('ManagedBy', ''),
                                    'TargetType': t_type,
                                    'TargetId': t.get('Id', ''),
                                    'TargetArn': t_arn,
                                    'EcsCluster': cluster,
                                    'EcsTaskDefinition': task_def,
                                    'EcsLaunchType': launch,
                                    'EcsTaskCount': task_count,
                                    'TargetInput': t_input,
                                }
                            )
                            matched += 1
                            print(f"  {t_type}: {rule_name} -> {t_arn}")
            except Exception as be:
                print(f"  Error on bus {bus_name}: {be}")
                continue

        print(f"  Matched ECS/Lambda targets in {region}: {matched}")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'eventbridge_rules_ecs_lambda_{ts}.csv'

fieldnames = [
    'Region',
    'EventBusName',
    'RuleName',
    'RuleArn',
    'State',
    'Description',
    'ScheduleExpression',
    'EventPattern',
    'ManagedBy',
    'TargetType',
    'TargetId',
    'TargetArn',
    'EcsCluster',
    'EcsTaskDefinition',
    'EcsLaunchType',
    'EcsTaskCount',
    'TargetInput',
]

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)

ecs_n = sum(1 for r in rows if r['TargetType'] == 'ecs')
lambda_n = sum(1 for r in rows if r['TargetType'] == 'lambda')

print(f"\nCSV exported: {csv_filename}")
print(f"Total rows: {len(rows)} (ECS targets: {ecs_n}, Lambda targets: {lambda_n})")
