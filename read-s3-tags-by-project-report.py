import boto3
import csv

# Initialize clients
s3 = boto3.client('s3')
sts = boto3.client('sts')

# Function to get the region of a bucket
def get_bucket_region(bucket_name):
    try:
        response = s3.get_bucket_location(Bucket=bucket_name)
        region = response.get('LocationConstraint')
        if region is None:
            return 'us-east-1'  # Default region
        return region
    except Exception as e:
        print(f"Error getting region for {bucket_name}: {e}")
        return 'Unknown'

# Function to get tags of a bucket
def get_bucket_tags(bucket_name):
    try:
        response = s3.get_bucket_tagging(Bucket=bucket_name)
        tags = response['TagSet']
        return {tag['Key']: tag['Value'] for tag in tags}
    except s3.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchTagSet':
            return {}
        else:
            print(f"Error retrieving tags for {bucket_name}: {e}")
            return {}

# List all buckets
response = s3.list_buckets()
buckets = response['Buckets']

buckets_without_project_tag = []

for bucket in buckets:
    name = bucket['Name']
    region = get_bucket_region(name)
    tags = get_bucket_tags(name)
    if 'Project' not in tags:
        buckets_without_project_tag.append({'BucketName': name, 'Region': region})

# Export to CSV
with open('buckets_without_project_tag.csv', mode='w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=['BucketName', 'Region'])
    writer.writeheader()
    for bucket in buckets_without_project_tag:
        writer.writerow(bucket)

print("Report generated: buckets_without_project_tag.csv")