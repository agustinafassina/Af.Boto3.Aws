import boto3
import json

cloudwatch = boto3.client('cloudwatch', region_name='sa-east-1')

alarms_response = cloudwatch.describe_alarms()

alarms_list = []
for alarm in alarms_response['MetricAlarms']:
    alarms_list.append({
        'AlarmName': alarm['AlarmName'],
        'StateValue': alarm['StateValue'],
        'MetricName': alarm['MetricName'],
        'Namespace': alarm['Namespace'],
        'Threshold': alarm['Threshold'],
        'ComparisonOperator': alarm['ComparisonOperator'],
        'Period': alarm['Period'],
        'EvaluationPeriods': alarm['EvaluationPeriods'],
        'ActionsEnabled': alarm['ActionsEnabled'],
        'AlarmDescription': alarm.get('AlarmDescription', ''),
        'OKActions': alarm['OKActions'],
        'AlarmActions': alarm['AlarmActions']
    })

print(json.dumps(alarms_list, indent=4))

with open('cloudwatch_alarms.json', 'w') as f:
    json.dump(alarms_list, f, indent=4)