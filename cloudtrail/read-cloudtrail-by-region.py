import boto3
import csv
from datetime import datetime

# Get all regions
ec2 = boto3.client('ec2', region_name='us-east-1')
regions_response = ec2.describe_regions()
regions = [r['RegionName'] for r in regions_response['Regions']]

cloudtrail_data = []

for region in regions:
    print(f"Checking region: {region}")

    try:
        ct = boto3.client('cloudtrail', region_name=region)
        response = ct.list_trails()

        trails = response.get('Trails', [])
        while response.get('NextToken'):
            response = ct.list_trails(NextToken=response['NextToken'])
            trails.extend(response.get('Trails', []))

        if not trails:
            cloudtrail_data.append({
                'Region': region,
                'TrailName': '',
                'TrailArn': '',
                'HomeRegion': '',
                'IsLogging': False,
                'CloudTrailEnabled': 'No',
            })
            print(f"  No trails in {region}")
            continue

        for trail in trails:
            trail_arn = trail.get('TrailARN', '')
            trail_name = trail.get('Name', '')
            home_region = trail.get('HomeRegion', '')

            try:
                status = ct.get_trail_status(Name=trail_arn)
                is_logging = status.get('IsLogging', False)
            except Exception as e:
                is_logging = False
                print(f"  Could not get status for {trail_name}: {e}")

            cloudtrail_data.append({
                'Region': region,
                'TrailName': trail_name,
                'TrailArn': trail_arn,
                'HomeRegion': home_region,
                'IsLogging': is_logging,
                'CloudTrailEnabled': 'Yes' if is_logging else 'No',
            })

        count = len([t for t in cloudtrail_data if t['Region'] == region])
        print(f"  Trails in {region}: {count}")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        cloudtrail_data.append({
            'Region': region,
            'TrailName': 'error',
            'TrailArn': '',
            'HomeRegion': '',
            'IsLogging': False,
            'CloudTrailEnabled': 'Error',
        })

# Export to CSV
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'cloudtrail_by_region_{ts}.csv'

csv_columns = ['Region', 'TrailName', 'TrailArn', 'HomeRegion', 'IsLogging', 'CloudTrailEnabled']

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=csv_columns)
    writer.writeheader()
    writer.writerows(cloudtrail_data)

# Summary: regions with at least one trail logging
regions_with_logging = set(
    row['Region'] for row in cloudtrail_data
    if row.get('IsLogging') is True
)
regions_without = [r for r in regions if r not in regions_with_logging]

print(f"\nCSV exported: {csv_filename}")
print(f"Regions with CloudTrail logging: {len(regions_with_logging)}")
print(f"Regions without CloudTrail logging: {len(regions_without)}")
if regions_without:
    print(f"  No logging: {', '.join(regions_without)}")
