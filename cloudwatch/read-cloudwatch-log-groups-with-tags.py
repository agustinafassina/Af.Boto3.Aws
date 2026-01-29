import boto3
import csv
from datetime import datetime

# Get all regions
ec2 = boto3.client('ec2')
regions_response = ec2.describe_regions()
regions = [region['RegionName'] for region in regions_response['Regions']]

# List to store all log groups with their tags
log_groups_data = []

# Function to get tags of a log group
def get_log_group_tags(logs_client, log_group_name):
    try:
        response = logs_client.list_tags_log_group(logGroupName=log_group_name)
        return response.get('tags', {})
    except Exception as e:
        print(f"Error retrieving tags for {log_group_name}: {e}")
        return {}

# Iterate through all regions
for region in regions:
    print(f"Checking region: {region}")
    
    try:
        logs = boto3.client('logs', region_name=region)
        
        # List all log groups in the region
        paginator = logs.get_paginator('describe_log_groups')
        
        for page in paginator.paginate():
            for log_group in page['logGroups']:
                log_group_name = log_group['logGroupName']
                
                # Get tags for the log group
                tags = get_log_group_tags(logs, log_group_name)
                
                # Format creation time
                creation_time = log_group.get('creationTime', '')
                if creation_time:
                    creation_time = datetime.fromtimestamp(creation_time / 1000).strftime('%Y-%m-%d %H:%M:%S')
                
                # Prepare data row
                row = {
                    'Region': region,
                    'LogGroupName': log_group_name,
                    'CreationTime': creation_time,
                    'RetentionInDays': log_group.get('retentionInDays', 'Never'),
                    'StoredBytes': log_group.get('storedBytes', 0),
                    'MetricFilterCount': log_group.get('metricFilterCount', 0),
                    'Arn': log_group.get('arn', ''),
                    'SizeInBytes': log_group.get('sizeInBytes', 0),
                    'KmsKeyId': log_group.get('kmsKeyId', '')
                }
                
                # Add tags as separate columns
                # Get all unique tag keys across all log groups first
                # For now, we'll add common tag keys and all found tags
                if tags:
                    for key, value in tags.items():
                        row[f'Tag_{key}'] = value
                
                log_groups_data.append(row)
        
        print(f"Found {len([lg for lg in log_groups_data if lg['Region'] == region])} log groups in {region}")
    
    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

# Get all unique tag keys to create consistent CSV columns
all_tag_keys = set()
for log_group in log_groups_data:
    for key in log_group.keys():
        if key.startswith('Tag_'):
            all_tag_keys.add(key)

# Sort tag keys for consistent column order
all_tag_keys = sorted(all_tag_keys)

# Define CSV columns
csv_columns = [
    'Region',
    'LogGroupName',
    'CreationTime',
    'RetentionInDays',
    'StoredBytes',
    'MetricFilterCount',
    'Arn',
    'SizeInBytes',
    'KmsKeyId'
] + list(all_tag_keys)

# Export to CSV
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'cloudwatch_log_groups_with_tags_{timestamp}.csv'

with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.DictWriter(file, fieldnames=csv_columns, extrasaction='ignore')
    writer.writeheader()
    
    for log_group in log_groups_data:
        writer.writerow(log_group)

print(f"\nReport generated: {csv_filename}")
print(f"Total log groups found: {len(log_groups_data)}")

