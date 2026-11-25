import boto3
import json

cloudwatch = boto3.client('cloudwatch', region_name='sa-east-1')

alarms_list = []
for page in cloudwatch.get_paginator('describe_alarms').paginate():
    # Metric math alarms have no MetricName/Namespace/Period at the top level
    for alarm in page['MetricAlarms']:
        alarms_list.append({
            'AlarmName': alarm['AlarmName'],
            'StateValue': alarm['StateValue'],
            'MetricName': alarm.get('MetricName', ''),
            'Namespace': alarm.get('Namespace', ''),
            'Threshold': alarm.get('Threshold', ''),
            'ComparisonOperator': alarm.get('ComparisonOperator', ''),
            'Period': alarm.get('Period', ''),
            'EvaluationPeriods': alarm.get('EvaluationPeriods', ''),
            'ActionsEnabled': alarm.get('ActionsEnabled', ''),
            'AlarmDescription': alarm.get('AlarmDescription', ''),
            'OKActions': alarm.get('OKActions', []),
            'AlarmActions': alarm.get('AlarmActions', []),
        })

print(json.dumps(alarms_list, indent=4))

with open('cloudwatch_alarms.json', 'w') as f:
    json.dump(alarms_list, f, indent=4)
