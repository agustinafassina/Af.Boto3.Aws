import boto3
import csv
import json
import sys
from datetime import datetime

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
    # arn:aws:service:region:account:resource...
    parts = arn.split(':')
    if len(parts) < 3:
        return ''
    service = parts[2]
    resource = parts[5] if len(parts) > 5 else ''
    if service == 'ecs':
        return 'ecs'
    if service == 'lambda':
        return 'lambda'
    if service == 'sqs':
        return 'sqs'
    if service == 'sns':
        return 'sns'
    if service == 'states':
        return 'stepfunctions'
    if service == 'events' and 'rule' in resource:
        return 'events'
    if service == 'logs':
        return 'logs'
    if service == 'codebuild':
        return 'codebuild'
    if service == 'ssm':
        return 'ssm'
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


rows = []

for region in regions:
    print(f"Checking region: {region}")

    try:
        events = boto3.client('events', region_name=region)
        buses = list_event_buses(events)

        for bus_name in buses:
            try:
                rule_paginator = events.get_paginator('list_rules')
                for page in rule_paginator.paginate(EventBusName=bus_name):
                    for rule in page.get('Rules', []):
                        rule_name = rule.get('Name', '')
                        schedule = rule.get('ScheduleExpression', '')
                        pattern = rule.get('EventPattern', '')
                        if pattern and len(pattern) > 500:
                            pattern = pattern[:500] + '...'

                        # Targets for this rule
                        targets = []
                        try:
                            next_token = None
                            while True:
                                kwargs = {
                                    'Rule': rule_name,
                                    'EventBusName': bus_name,
                                }
                                if next_token:
                                    kwargs['NextToken'] = next_token
                                tresp = events.list_targets_by_rule(**kwargs)
                                targets.extend(tresp.get('Targets', []))
                                next_token = tresp.get('NextToken')
                                if not next_token:
                                    break
                        except Exception as te:
                            targets = []
                            print(f"  list_targets_by_rule {rule_name}: {te}")

                        if not targets:
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
                                    'TargetId': '',
                                    'TargetArn': '',
                                    'TargetType': '',
                                    'TargetInput': '',
                                }
                            )
                            continue

                        for t in targets:
                            t_arn = t.get('Arn', '')
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
                                    'TargetId': t.get('Id', ''),
                                    'TargetArn': t_arn,
                                    'TargetType': target_type_from_arn(t_arn),
                                    'TargetInput': t_input,
                                }
                            )
            except Exception as be:
                print(f"  Error on bus {bus_name}: {be}")
                continue

        n_rules = len({(r['Region'], r['EventBusName'], r['RuleName']) for r in rows if r['Region'] == region})
        n_rows = len([r for r in rows if r['Region'] == region])
        print(f"  EventBridge in {region}: {n_rules} rules, {n_rows} rule/target rows")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'eventbridge_rules_inventory_{ts}.csv'

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
    'TargetId',
    'TargetArn',
    'TargetType',
    'TargetInput',
]

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)

scheduled = len(
    {
        (r['Region'], r['EventBusName'], r['RuleName'])
        for r in rows
        if r.get('ScheduleExpression')
    }
)
enabled = len(
    {
        (r['Region'], r['EventBusName'], r['RuleName'])
        for r in rows
        if r.get('State') == 'ENABLED'
    }
)

print(f"\nCSV exported: {csv_filename}")
print(f"Total rule/target rows: {len(rows)}")
print(f"Unique rules with ScheduleExpression: {scheduled}")
print(f"Unique ENABLED rules: {enabled}")
