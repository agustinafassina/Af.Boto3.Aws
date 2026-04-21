"""
List ECS clusters with attached capacity providers and default capacity provider strategy.
Enriches provider names with describe_capacity_providers (EC2 ASG vs Fargate-style).

Usage:
  python ecs/read-ecs-capacity-providers-by-cluster.py
  python ecs/read-ecs-capacity-providers-by-cluster.py sa-east-1
"""
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


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


rows = []

for region in regions:
    print(f"Checking region: {region}")

    try:
        ecs = boto3.client('ecs', region_name=region)

        cluster_arns = []
        for page in ecs.get_paginator('list_clusters').paginate():
            cluster_arns.extend(page.get('clusterArns', []))

        all_cp_names = set()
        cluster_payloads = []

        for chunk in chunks(cluster_arns, 100):
            for c in ecs.describe_clusters(clusters=chunk).get('clusters', []):
                cps = c.get('capacityProviders') or []
                for n in cps:
                    all_cp_names.add(n)
                cluster_payloads.append(
                    {
                        'cluster': c,
                        'cps': cps,
                        'strat': c.get('defaultCapacityProviderStrategy') or [],
                    }
                )

        cp_detail_cache = {}
        for cp_chunk in chunks(sorted(all_cp_names), 100):
            if not cp_chunk:
                break
            try:
                d = ecs.describe_capacity_providers(capacityProviders=cp_chunk)
                for cp in d.get('capacityProviders', []):
                    n = cp.get('name', '')
                    if n in ('FARGATE', 'FARGATE_SPOT'):
                        cp_detail_cache[n] = 'FARGATE_BUILTIN'
                    elif cp.get('autoScalingGroupProvider'):
                        cp_detail_cache[n] = 'EC2_ASG'
                    else:
                        cp_detail_cache[n] = 'CUSTOM_OR_UNKNOWN'
            except Exception as e:
                print(f"  describe_capacity_providers warning: {e}")

        for item in cluster_payloads:
            c = item['cluster']
            cps = item['cps']
            strat = item['strat']
            cp_types = [f"{n}:{cp_detail_cache.get(n, '?')}" for n in cps]

            rows.append(
                {
                    'Region': region,
                    'ClusterName': c.get('clusterName', ''),
                    'ClusterArn': c.get('clusterArn', ''),
                    'CapacityProviders': ','.join(cps),
                    'CapacityProviderTypes': ','.join(cp_types) if cp_types else '',
                    'DefaultCapacityProviderStrategy': json.dumps(strat, separators=(',', ':')),
                }
            )

        n = len([r for r in rows if r['Region'] == region])
        print(f"  Clusters in {region}: {n}")

    except Exception as e:
        print(f"Error processing region {region}: {e}")
        continue

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_filename = f'ecs_capacity_providers_by_cluster_{ts}.csv'

fieldnames = [
    'Region',
    'ClusterName',
    'ClusterArn',
    'CapacityProviders',
    'CapacityProviderTypes',
    'DefaultCapacityProviderStrategy',
]

with open(csv_filename, mode='w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)

print(f"\nCSV exported: {csv_filename}")
print(f"Total clusters: {len(rows)}")
