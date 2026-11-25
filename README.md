# ☁️ Af.Boto3.Aws scripts

Python scripts using **boto3** (AWS SDK) to audit, inventory and analyze AWS resources. All scripts are **read-only**: they never create, modify or delete resources.

## 📑 Contents

- [Getting started](#getting-started)
- [Usage](#usage)
- Scripts: [ACM](#acm) · [CloudTrail](#cloudtrail) · [CloudWatch](#cloudwatch) · [DynamoDB](#dynamodb) · [EC2](#ec2) · [ECR](#ecr) · [ECS](#ecs) · [EventBridge](#eventbridge) · [IAM](#iam) · [Inventory by region](#by-region) · [Lambda](#lambda) · [RDS](#rds) · [Route 53](#route53) · [S3](#s3) · [Secrets Manager](#secretsmanager) · [Security groups](#security-groups)
- [Planned additions](#planned-additions)

<a id="getting-started"></a>

## 🚀 Getting started

### Requirements

- Python 3.8+
- AWS credentials configured locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Credentials

The scripts use the standard boto3 credential chain, so any of these work:

```bash
aws configure                    # access keys
aws sso login --profile my-prof  # IAM Identity Center / SSO
export AWS_PROFILE=my-prof       # Windows PowerShell: $env:AWS_PROFILE="my-prof"
```

### IAM permissions

Read-only access is enough. The AWS managed policies **`ReadOnlyAccess`** or **`SecurityAudit`** + **`ViewOnlyAccess`** cover all scripts.

<a id="usage"></a>

## ▶️ Usage

Run scripts from the repository root:

```bash
python <folder>/<script>.py [arguments]
```

- **`[region]`**: scripts that accept it scan only that region (e.g. `sa-east-1`); without it they scan **all enabled regions**.
- **`[days]`**: age or warning threshold in days; each script documents its default.
- **Output**: CSV/JSON reports are written to the **current directory**, most with a `_<YYYYmmdd_HHMMSS>` timestamp suffix. They are ignored by git because they may contain account data (ARNs, IPs, user names).

> ⚠️ Scripts that flag resources as unused or old (task definitions, ECR images, snapshots, volumes, security groups) are **hints, not proof**. Review the report before deleting anything.

## 📜 Scripts

<a id="acm"></a>

### 🔐 ACM (`acm/`)

| Script | Arguments | Description |
|--------|-----------|-------------|
| **read-acm-certificates-expiration.py** | `[days]` (default 90) | Lists **ACM certificates** in all regions with **NotAfter**, **DaysUntilExpiry** and **ExpiringWithinWarnDays** (Yes / No / Expired). Prints certificates expiring within the window. Output: `acm_certificates_expiration_<ts>.csv`. |

<a id="cloudtrail"></a>

### 🕵️ CloudTrail (`cloudtrail/`)

| Script | Arguments | Description |
|--------|-----------|-------------|
| **read-cloudtrail-by-region.py** | — | Lists CloudTrail **trails per region** and whether each is logging (Region, TrailName, TrailArn, HomeRegion, IsLogging, CloudTrailEnabled). Prints regions with and without logging. Output: `cloudtrail_by_region_<ts>.csv`. |

<a id="cloudwatch"></a>

### 📊 CloudWatch (`cloudwatch/`)

| Script | Arguments | Description |
|--------|-----------|-------------|
| **read-cloudwatch.py** | — | Lists all CloudWatch **alarms** in `sa-east-1` (name, state, metric, threshold, actions, etc.). Output: `cloudwatch_alarms.json`. |
| **read-cloudwatch-log-groups-with-tags.py** | — | Lists all CloudWatch Logs **log groups** in all regions with metadata (retention, size, etc.) and their **tags** as dynamic columns. Output: `cloudwatch_log_groups_with_tags_<ts>.csv`. |

<a id="dynamodb"></a>

### 🗃️ DynamoDB (`dynamodb/`)

| Script | Arguments | Description |
|--------|-----------|-------------|
| **read-dynamodb-tables-inventory.py** | `[region]` | Lists **DynamoDB tables** with billing mode, RCU/WCU, size, item count, stream, SSE, GSI/LSI counts, creation time, **TTL** status and **PITR**. Prints count with PITR enabled. Output: `dynamodb_tables_inventory_<ts>.csv`. |

<a id="ec2"></a>

### 🖥️ EC2 (`ec2/`)

| Script | Arguments | Description |
|--------|-----------|-------------|
| **read-ec2-filter-by-tag-all-region.py** | — | Lists EC2 instances that **do not have** the `Project` tag in all regions. Console output only. |
| **read-ec2-filter-by-account.py** | — | Audits resources without the `Project` tag in all regions: EC2 instances, EBS volumes, security groups, Elastic IPs, ECR repositories and AWS Config rules. Console output only. |
| **read-ec2-unused-security-groups.py** | — | Lists **all** security groups and whether each is **in use** (attached to a network interface). Output: `unused_security_groups_<ts>.csv`. |
| **read-ec2-unattached-ebs-volumes.py** | — | Lists EBS volumes **not attached** to any instance (state `available`). Prints total count and size (Gb) for cost visibility. Output: `unattached_ebs_volumes_<ts>.csv`. |
| **read-ec2-unassociated-elastic-ips.py** | — | Lists **Elastic IPs not associated** with any instance. Useful to release IPs and avoid charges. Output: `unassociated_elastic_ips_<ts>.csv`. |
| **read-ec2-snapshots-older-than-days.py** | `[days]` (default 90) | Lists **EBS snapshots** owned by the account older than N days. Prints total count and size (Gb). Output: `ebs_snapshots_older_than_<N>_days_<ts>.csv`. |
| **read-ec2-elbv2-by-region.py** | — | Lists **Application / Network / Gateway** load balancers (ELBv2): name, ARN, type, scheme, state, VPC, DNS name, IP address type, created time. Output: `elbv2_load_balancers_<ts>.csv`. |

<a id="ecr"></a>

### 📦 ECR (`ecr/`)

| Script | Arguments | Description |
|--------|-----------|-------------|
| **read-ecr-images-not-in-ecs-task-definitions.py** | `[region]` | Lists **ECR images** that do **not** match any **ACTIVE** ECS task definition image (ECS is always scanned in all regions; the argument filters ECR). Set `INCLUDE_INACTIVE_TASK_DEFINITIONS` at the top of the script to also consider inactive revisions. Heavy on `DescribeTaskDefinition` calls. Output: `ecr_images_not_in_ecs_task_definitions_<ts>.csv`. |
| **read-ecr-untagged-images.py** | `[region] [days]` (default 0) | Lists **ECR images without tags** (digest-only), optionally only those pushed more than N days ago. Output: `ecr_untagged_images_<ts>.csv`. |
| **read-ecr-repository-summary.py** | `[region]` | **Per-repository** summary: image count, tagged vs untagged, total size (Gb), URI, created date, scan-on-push. Output: `ecr_repository_summary_<ts>.csv`. |
| **read-ecr-image-scan-summary.py** | `[region]` | **Basic scanning** summary per image: scan status and finding counts by severity (CRITICAL → UNDEFINED). Many API calls with many images. Output: `ecr_image_scan_summary_<ts>.csv`. |

<a id="ecs"></a>

### 🐳 ECS (`ecs/`)

| Script | Arguments | Description |
|--------|-----------|-------------|
| **read-ecs-inventory.py** | `[region]` | **ECS inventory** in three CSVs with the same timestamp: `ecs_clusters_<ts>.csv` (counts and status), `ecs_services_<ts>.csv` (desired/running/pending, task definition, launch type, Fargate platform, deployment %), `ecs_running_tasks_<ts>.csv` (task definition, started time, CPU/memory, container images). |
| **read-ecs-unused-task-definitions.py** | `[region]` | Lists **ACTIVE** task definition revisions **not** referenced by any service (including rollouts) or **RUNNING** task. Does not consider EventBridge schedules, Step Functions or finished RunTask calls. Output: `ecs_unused_task_definitions_<ts>.csv`. |
| **read-ecs-capacity-providers-by-cluster.py** | `[region]` | Lists each **cluster** with its capacity providers, **defaultCapacityProviderStrategy** (JSON) and a best-effort type (`FARGATE_BUILTIN`, `EC2_ASG`, `CUSTOM_OR_UNKNOWN`). Output: `ecs_capacity_providers_by_cluster_<ts>.csv`. |

<a id="eventbridge"></a>

### ⏰ EventBridge (`eventbridge/`)

| Script | Arguments | Description |
|--------|-----------|-------------|
| **read-eventbridge-rules-inventory.py** | `[region]` | Lists **EventBridge rules** on all event buses, one row per rule/target: bus, rule, state, **ScheduleExpression**, EventPattern (truncated), ManagedBy, target type (ecs, lambda, sqs, sns, stepfunctions, etc.) and input snippet. Output: `eventbridge_rules_inventory_<ts>.csv`. |
| **read-eventbridge-rules-ecs-lambda.py** | `[region]` | Same scan, **only rules with ECS or Lambda targets**, plus ECS columns (cluster, task definition, launch type, task count). Output: `eventbridge_rules_ecs_lambda_<ts>.csv`. |

<a id="iam"></a>

### 🔑 IAM (`iam/`)

| Script | Arguments | Description |
|--------|-----------|-------------|
| **read-iam-users.py** | — | Lists all IAM users with groups and attached policies. JSON to the console. |
| **read-iam-users-with-access-keys.py** | — | Lists users with **one or more access keys** (status, create date, age). Prints active/inactive summary and the oldest key. Output: `iam_users_with_access_keys_<ts>.csv`. |
| **read-export-iam.py** | — | Exports all users with groups, policies (direct and via groups) and tags (`Project`, `ProjectStatus`, `ProjectService`, `ProjectDescription`). Output: `users_iam_tags_permisos.csv`. |
| **read-iam-users-without-mfa.py** | — | Lists users **without MFA** enabled. Output: `iam_users_without_mfa_<ts>.csv`. |
| **read-iam-access-keys-older-than-90-days.py** | — | Lists access keys **older than 90 days** for rotation (change `IAM_ACCESS_KEY_MAX_AGE_DAYS` at the top of the script). Output: `iam_access_keys_older_than_<N>_days_<ts>.csv`. |

<a id="by-region"></a>

### 🧾 Inventory by region (`by-region/`)

| Script | Arguments | Description |
|--------|-----------|-------------|
| **list-resources.py** | — | Regional inventory for the **`REGION`** constant at the top of the file (default `sa-east-1`): EC2 (instances, volumes, security groups, VPCs, AMIs, snapshots), RDS, Lambda, ECR, S3 and CloudWatch Logs. Prints a count by service/type. Output: `resources_<REGION>_<ts>.csv`. |

<a id="lambda"></a>

### λ Lambda (`lambda/`)

| Script | Arguments | Description |
|--------|-----------|-------------|
| **read-lambda-functions-inventory.py** | `[region]` | Lists **Lambda functions**: runtime, handler, package type, role, memory, timeout, ephemeral storage, architectures, last modified, code size, VPC, layer count, state and tags. Output: `lambda_functions_inventory_<ts>.csv`. |

<a id="rds"></a>

### 🗄️ RDS (`rds/`)

| Script | Arguments | Description |
|--------|-----------|-------------|
| **read-rds-by-region.py** | `[region]` | Lists RDS instances: engine and version, class, status, endpoint, storage, Multi-AZ, VPC, AZ, ARN. Output: `rds_by_region_<ts>.csv`. |
| **read-rds-public-private.py** | `[region]` | Lists RDS instances as **Public** or **Private** (`PubliclyAccessible`). Prints the count of each. Output: `rds_public_private_<ts>.csv`. |
| **read-rds-snapshots-older-than-days.py** | `[days] [region]` (default 90) | Lists **RDS snapshots** (instance and Aurora cluster, manual and automated) older than N days. Prints totals, manual count, size and unencrypted count. Output: `rds_snapshots_older_than_<N>_days_<ts>.csv`. |
| **read-rds-backup-encryption-audit.py** | `[region]` | Audits instances for **automated backups** (`BackupRetentionPeriod` = 0 means disabled) and **storage encryption** (Aurora members use cluster values). Includes a **Findings** column (`NoAutomatedBackups`, `NotEncrypted`). Output: `rds_backup_encryption_audit_<ts>.csv`. |

<a id="route53"></a>

### 🌍 Route 53 (`route53/`)

| Script | Arguments | Description |
|--------|-----------|-------------|
| **read-route53-list-zones-and-records.py** | — | Lists all **hosted zones** and their **record sets**. Output: `route53_hosted_zones_<ts>.csv` (zone, record count, private flag) and `route53_record_sets_<ts>.csv` (record name, type, TTL, value). |

<a id="s3"></a>

### 🪣 S3 (`s3/`)

| Script | Arguments | Description |
|--------|-----------|-------------|
| **read-s3-tags-by-project-report.py** | — | Lists buckets that **do not have** the `Project` tag, with their region. Output: `buckets_without_project_tag.csv`. |
| **read-s3-public-access-block.py** | — | Lists **all buckets** with their **Block Public Access** flags (or `not_configured`) and **FullyBlocked** (Yes/No). Prints buckets that need review. Output: `s3_public_access_block_<ts>.csv`. |

<a id="secretsmanager"></a>

### 🤐 Secrets Manager (`secretsmanager/`)

| Script | Arguments | Description |
|--------|-----------|-------------|
| **read-secrets-manager-inventory.py** | `[region]` | Lists **secrets metadata** (never secret values): rotation settings, rotation Lambda, KMS key, last changed/rotated/accessed, pending deletion, owning service, version count, tags. Prints the count with rotation disabled. Output: `secrets_manager_inventory_<ts>.csv`. |

<a id="security-groups"></a>

### 🛡️ Security groups (root)

| Script | Arguments | Description |
|--------|-----------|-------------|
| **read-security-groups.py** | — | Lists security groups in `sa-east-1` with **open** rules (ingress or egress to `0.0.0.0/0` or `::/0`). Output: `security_groups_open.csv`. |

<a id="planned-additions"></a>

## 🗺️ Planned additions

- Automated backup of EC2 instances or EBS volumes, filtered by tags or regions.
- AWS cost reports filtered by resource tags.
- NAT Gateways / ENIs unassociated (cost cleanup).
- EventBridge Scheduler schedules (complement to Rules).
