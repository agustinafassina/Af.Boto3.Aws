# Af.Boto3.Aws
This repository contains several Python scripts using boto3, the official AWS SDK for Python, to automate common tasks and perform analysis in the cloud.

### Scripts detail

- EC2 Instances Filter by Tag: lists all instances across the account that have a specific tag.
- EC2 Instances in the Entire Account: lists all instances grouped by tag across the account, without restricting to a single instance.
- Read security groups with all open.
- CloudWatch Alarms List: provides information on all configured CloudWatch alarms.
- Vulnerabilities reading in Amazon Inspector: retrieves active findings in images or resources within the account.

Pendig a sumar:
- Backup automático de instancias EC2 o volúmenes EBS, filtrando por tags o regiones.
- Montar reportes de costos en AWS, filtrando por tags de recursos.
- Verificación del estado y rendimiento en otros servicios, como RDS o Lambda.
- Control de accesos y permisos, auditando configuraciones IAM.