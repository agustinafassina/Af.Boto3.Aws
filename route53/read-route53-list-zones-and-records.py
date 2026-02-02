import boto3
import csv
from datetime import datetime

# Route 53 is a global service; client uses us-east-1
route53 = boto3.client('route53', region_name='us-east-1')

zones_data = []
records_data = []

print("Listing hosted zones...")

paginator = route53.get_paginator('list_hosted_zones')
for page in paginator.paginate():
    for zone in page.get('HostedZones', []):
        zone_id = zone['Id'].replace('/hostedzone/', '')
        zone_name = zone['Name'].rstrip('.')
        record_count = zone.get('ResourceRecordSetCount', 0)
        is_private = zone.get('Config', {}).get('PrivateZone', False)

        zones_data.append({
            'HostedZoneId': zone_id,
            'Name': zone_name,
            'ResourceRecordSetCount': record_count,
            'PrivateZone': is_private,
        })

# List record sets per zone (domains by zone)
for zone in zones_data:
    try:
        rec_paginator = route53.get_paginator('list_resource_record_sets')
        for rec_page in rec_paginator.paginate(HostedZoneId=zone['HostedZoneId']):
            for rr_set in rec_page.get('ResourceRecordSets', []):
                name = rr_set.get('Name', '').rstrip('.')
                rtype = rr_set.get('Type', '')
                ttl = rr_set.get('TTL', '')
                # AliasTarget has different structure
                resource_records = rr_set.get('ResourceRecords', [])
                alias = rr_set.get('AliasTarget', {})
                if resource_records:
                    values = ' | '.join(r.get('Value', '') for r in resource_records)
                elif alias:
                    values = alias.get('DNSName', '') or alias.get('HostedZoneId', '')
                else:
                    values = ''

                records_data.append({
                    'HostedZoneId': zone['HostedZoneId'],
                    'ZoneName': zone['Name'],
                    'RecordName': name,
                    'Type': rtype,
                    'TTL': ttl,
                    'Value': values[:500] if values else '',  # truncate long values
                })
    except Exception as e:
        print(f"Error listing records for zone {zone['HostedZoneId']}: {e}")

ts = datetime.now().strftime('%Y%m%d_%H%M%S')

# Export hosted zones CSV
if zones_data:
    zones_file = f'route53_hosted_zones_{ts}.csv'
    with open(zones_file, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['HostedZoneId', 'Name', 'ResourceRecordSetCount', 'PrivateZone'])
        w.writeheader()
        w.writerows(zones_data)
    print(f"Saved: {zones_file} ({len(zones_data)} zones)")
else:
    print("No hosted zones found.")

# Export record sets CSV (domains by zone)
if records_data:
    records_file = f'route53_record_sets_{ts}.csv'
    with open(records_file, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['HostedZoneId', 'ZoneName', 'RecordName', 'Type', 'TTL', 'Value'])
        w.writeheader()
        w.writerows(records_data)
    print(f"Saved: {records_file} ({len(records_data)} records)")
else:
    print("No record sets found.")
