import boto3
import csv

ec2 = boto3.client('ec2', region_name='sa-east-1')

response = ec2.describe_security_groups()

open_sg = []

for sg in response['SecurityGroups']:
    sg_id = sg['GroupId']
    sg_name = sg.get('GroupName', 'N/A')
    ingress_rules = sg['IpPermissions']
    egress_rules = sg['IpPermissionsEgress']

    def check_rules(rules, direction='Ingress'):
        for rule in rules:

            for ip_range in rule.get('IpRanges', []):
                cidr = ip_range.get('CidrIp')
                if cidr == '0.0.0.0/0':
                    open_sg.append({ 'SG ID': sg_id, 'SG Name': sg_name, 'Direction': direction, 'CIDR': cidr })

            for ipv6_range in rule.get('Ipv6Ranges', []):
                cidr6 = ipv6_range.get('CidrIpv6')
                if cidr6 == '::/0':
                    open_sg.append({ 'SG ID': sg_id, 'SG Name': sg_name, 'Direction': direction, 'CIDR': cidr6 })

    check_rules(ingress_rules, 'Ingress')
    check_rules(egress_rules, 'Egress')

with open('security_groups_open.csv', 'w', newline='') as csvfile:
    fieldnames = ['SG ID', 'SG Name', 'Direction', 'CIDR']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    for row in open_sg:
        writer.writerow(row)

print("File 'security_groups_open.csv' successfully generated.")