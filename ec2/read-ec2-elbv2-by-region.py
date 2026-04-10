import boto3
import csv
from datetime import datetime

ec2 = boto3.client('ec2', region_name='us-east-1')
regions_response = ec2.describe_regions()
regions = [region['RegionName'] for region in regions_response['Regions']]

load_balancers = []

for region in regions:
    print(f"Checking region: {region}")

    try:
        elbv2 = boto3.client('elbv2', region_name=region)
        paginator = elbv2.get_paginator('describe_load_balancers')
        for page in paginator.paginate():
            for lb in page.get('LoadBalancers', []):
                state = lb.get('State', {}).get('Code', '')
                created = lb.get('CreatedTime', '')
                if created:
                    created = created.strftime('%Y-%m-%d %H:%M:%S')

                load_balancers.append({
                    'Region': region,
                    'LoadBalancerName': lb.get('LoadBalancerName', ''),
                    'LoadBalancerArn': lb.get('LoadBalancerArn', ''),
                    'Type': lb.get('Type', ''),
                    'Scheme': lb.get('Scheme', ''),
                    'State': state,
                    'VpcId': lb.get('VpcId', ''),
                    'DNSName': lb.get('DNSName', ''),
                    'IpAddressType': lb.get('IpAddressType', ''),
                    'CreatedTime': created,
                })

        count = len([x for x in load_balancers if x['Region'] == region])
        print(f"  Load balancers in {region}: {count}")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'elbv2_load_balancers_{ts}.csv'

csv_columns = [
    'Region',
    'LoadBalancerName',
    'LoadBalancerArn',
    'Type',
    'Scheme',
    'State',
    'VpcId',
    'DNSName',
    'IpAddressType',
    'CreatedTime',
]

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=csv_columns)
    writer.writeheader()
    writer.writerows(load_balancers)

print(f"\nCSV exported: {csv_filename}")
print(f"Total load balancers: {len(load_balancers)}")
