import boto3
import csv
from datetime import datetime

# Get all regions
ec2 = boto3.client('ec2', region_name='us-east-1')
regions_response = ec2.describe_regions()
regions = [region['RegionName'] for region in regions_response['Regions']]

unassociated_ips = []

for region in regions:
    print(f"Checking region: {region}")

    try:
        regional_ec2 = boto3.client('ec2', region_name=region)
        response = regional_ec2.describe_addresses()

        for addr in response.get('Addresses', []):
            # Unassociated = not attached to any instance
            if addr.get('AssociationId'):
                continue

            unassociated_ips.append({
                'Region': region,
                'AllocationId': addr.get('AllocationId', ''),
                'PublicIp': addr.get('PublicIp', ''),
                'Domain': addr.get('Domain', 'vpc'),
            })

        count = len([a for a in unassociated_ips if a['Region'] == region])
        print(f"  Unassociated Elastic IPs in {region}: {count}")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

# Export to CSV
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'unassociated_elastic_ips_{ts}.csv'

csv_columns = ['Region', 'AllocationId', 'PublicIp', 'Domain']

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=csv_columns)
    writer.writeheader()
    writer.writerows(unassociated_ips)

print(f"\nCSV exported: {csv_filename}")
print(f"Total unassociated Elastic IPs: {len(unassociated_ips)}")
