import boto3
import csv
import sys
from datetime import datetime, timezone

# Warn in console for certificates expiring within this many days (optional first arg, default 90)
WARN_WITHIN_DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 90

ec2 = boto3.client('ec2', region_name='us-east-1')
regions_response = ec2.describe_regions()
regions = [r['RegionName'] for r in regions_response['Regions']]

rows = []


def utc_now():
    return datetime.now(timezone.utc)


for region in regions:
    print(f"Checking region: {region}")

    try:
        acm = boto3.client('acm', region_name=region)
        paginator = acm.get_paginator('list_certificates')

        for page in paginator.paginate():
            for summary in page.get('CertificateSummaryList', []):
                arn = summary.get('CertificateArn', '')
                domain = summary.get('DomainName', '')
                status = summary.get('Status', '')
                cert_type = summary.get('Type', '')

                not_after = None
                not_after_str = ''
                days_until_expiry = ''
                expiring_soon = ''

                try:
                    detail = acm.describe_certificate(CertificateArn=arn)
                    cert = detail.get('Certificate', {})
                    not_after = cert.get('NotAfter')
                    if not_after:
                        if not_after.tzinfo is None:
                            not_after = not_after.replace(tzinfo=timezone.utc)
                        not_after_str = not_after.strftime('%Y-%m-%d %H:%M:%S')
                        delta = not_after - utc_now()
                        days = delta.days
                        days_until_expiry = str(days)
                        if days < 0:
                            expiring_soon = 'Expired'
                        elif days <= WARN_WITHIN_DAYS:
                            expiring_soon = 'Yes'
                            print(f"  Expires within {WARN_WITHIN_DAYS} days: {domain} ({region}, {days} days)")
                        else:
                            expiring_soon = 'No'
                except Exception as e:
                    not_after_str = f'error: {e}'

                rows.append({
                    'Region': region,
                    'DomainName': domain,
                    'CertificateArn': arn,
                    'Status': status,
                    'Type': cert_type,
                    'NotAfter': not_after_str,
                    'DaysUntilExpiry': days_until_expiry,
                    'ExpiringWithinWarnDays': expiring_soon,
                })

        count = len([r for r in rows if r['Region'] == region])
        if count:
            print(f"  ACM certificates in {region}: {count}")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'acm_certificates_expiration_{ts}.csv'

csv_columns = [
    'Region',
    'DomainName',
    'CertificateArn',
    'Status',
    'Type',
    'NotAfter',
    'DaysUntilExpiry',
    'ExpiringWithinWarnDays',
]

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=csv_columns)
    writer.writeheader()
    writer.writerows(rows)

need_attention = [r for r in rows if r.get('ExpiringWithinWarnDays') in ('Yes', 'Expired')]
print(f"\nCSV exported: {csv_filename}")
print(f"Total ACM certificates: {len(rows)}")
print(f"Expired or expiring within {WARN_WITHIN_DAYS} days: {len(need_attention)}")
