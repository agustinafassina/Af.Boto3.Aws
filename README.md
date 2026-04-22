# ☁️ Af.Boto3.Aws
Python scripts using **boto3** (AWS SDK) to automate tasks and analyze resources in the cloud.

---

### 📋 Script descriptions
#### 🖥️ EC2 (`ec2/`)
| Script | Description |
|--------|-------------|
| **read-ec2-filter-by-tag-all-region.py** | Iterates over all regions and lists EC2 instances that **do not have** the `Project` tag. Outputs InstanceIds per region. |
| **read-ec2-filter-by-account.py** | Iterates over all regions and audits resources without the `Project` tag: EC2 instances, EBS volumes, security groups, Elastic IPs, ECR repositories, and AWS Config rules. Prints untagged resources to the console. |
| **read-ec2-unused-security-groups.py** | Lists **all** security groups in all regions and indicates whether each is in use (attached to a network interface) or not. Exports a CSV with columns: Region, GroupId, GroupName, VpcId, Description, IsDefault, **InUse** (Yes/No). |
| **read-ec2-unattached-ebs-volumes.py** | Lists EBS volumes that are **not attached** to any instance (state `available`) in all regions. Exports a CSV with Region, VolumeId, SizeGb, VolumeType, State, AvailabilityZone, CreateTime, SnapshotId, Tags. Prints total count and total size (Gb) for cost visibility. |
| **read-ec2-unassociated-elastic-ips.py** | Lists **Elastic IPs not associated** with any instance in all regions. Exports a CSV with Region, AllocationId, PublicIp, Domain. Useful to release IPs and avoid charges. |
| **read-ec2-snapshots-older-than-days.py** | Lists **EBS snapshots** owned by the account older than N days (default **90**; optional first argument). Exports a CSV with Region, SnapshotId, VolumeId, VolumeSizeGb, StartTime, AgeInDays, Description, Tags. Prints total count and total size (Gb). |
| **read-ec2-elbv2-by-region.py** | Lists **Application / Network / Gateway** load balancers (ELBv2) in all regions. Exports a CSV with Region, name, ARN, Type, Scheme, State, VpcId, DNSName, IpAddressType, CreatedTime. |

#### CloudTrail (`cloudtrail/`)
| Script | Description |
|--------|-------------|
| **read-cloudtrail-by-region.py** | Lists CloudTrail **trails per region** and whether each is logging. Exports a CSV with Region, TrailName, TrailArn, HomeRegion, IsLogging, CloudTrailEnabled. Prints regions with and without CloudTrail logging. |

#### 🔐 ACM (`acm/`)
| Script | Description |
|--------|-------------|
| **read-acm-certificates-expiration.py** | Lists **ACM certificates** in all regions with **NotAfter**, **DaysUntilExpiry**, and **ExpiringWithinWarnDays** (Yes / No / Expired). Default warning window is **90 days** (optional first argument). Exports `acm_certificates_expiration_<timestamp>.csv`. Prints certificates expiring within that window. Run: `python acm/read-acm-certificates-expiration.py` or `python acm/read-acm-certificates-expiration.py 30`. |

#### 🐳 ECS (`ecs/`)
| Script | Description |
|--------|-------------|
| **read-ecs-inventory.py** | **ECS inventory** across all regions (or one region if passed as argument). Exports three CSVs with the same timestamp: `ecs_clusters_*.csv` (cluster counts and status), `ecs_services_*.csv` (desired/running/pending, task definition, launch type, Fargate platform, deployment %), `ecs_running_tasks_*.csv` (task ARN, task definition, started time, CPU/memory, container images). Run: `python ecs/read-ecs-inventory.py` or `python ecs/read-ecs-inventory.py sa-east-1`. |
| **read-ecs-unused-task-definitions.py** | Lists **ACTIVE** task definition revisions **not** referenced by any service (including deployment rollouts) or **RUNNING** task in that region. Exports `ecs_unused_task_definitions_<timestamp>.csv`. Does not consider EventBridge schedules, Step Functions, or finished RunTask—verify before deregistering. Run: `python ecs/read-ecs-unused-task-definitions.py` or with a region argument. |
| **read-ecs-capacity-providers-by-cluster.py** | Lists each **ECS cluster** with `capacityProviders`, **defaultCapacityProviderStrategy** (JSON), and a best-effort type map (`EC2_ASG` vs `FARGATE_OR_CUSTOM`) via `describe_capacity_providers`. Exports `ecs_capacity_providers_by_cluster_<timestamp>.csv`. |

#### 📦 ECR (`ecr/`)
| Script | Description |
|--------|-------------|
| **read-ecr-images-not-in-ecs-task-definitions.py** | Lists **ECR images** (per repository) that do **not** match any **ACTIVE** ECS task definition `containerDefinitions[].image` string (scans ECS in **all** regions, then ECR in all regions or one region if passed as argument). Exports `ecr_images_not_in_ecs_task_definitions_<timestamp>.csv` with digest, tags, pushed date. Optional `INCLUDE_INACTIVE_TASK_DEFINITIONS` at top of script. Heavy on `DescribeTaskDefinition` API—review CSV before lifecycle delete. |
| **read-ecr-untagged-images.py** | Lists **ECR images without tags** (digest-only) per repository. Optional **minimum age in days** since push (second argument): `python ecr/read-ecr-untagged-images.py sa-east-1 30`. Exports `ecr_untagged_images_<timestamp>.csv` with digest, pushed time, age, size. |
| **read-ecr-repository-summary.py** | **Per-repository** summary in all regions (or one region): image count, tagged vs untagged counts, sum of `imageSizeInBytes` (approximate Gb column), repo URI, created date, scan-on-push. Exports `ecr_repository_summary_<timestamp>.csv`. |
| **read-ecr-image-scan-summary.py** | **ECR basic scanning** summary per image: scan status, `findingSeverityCounts` (CRITICAL/HIGH/MEDIUM/LOW/INFORMATIONAL/UNDEFINED) via `describe_image_scan_findings`. One row per image from `describe_images`; non-`COMPLETE` scans get counts empty. Many API calls if many images. Exports `ecr_image_scan_summary_<timestamp>.csv`. |

#### 📊 CloudWatch (`cloudwatch/`)
| Script | Description |
|--------|-------------|
| **read-cloudwatch.py** | Lists all CloudWatch alarms in region `sa-east-1`. Outputs a JSON with name, state, metric, threshold, actions, etc. and saves `cloudwatch_alarms.json`. |
| **read-cloudwatch-log-groups-with-tags.py** | Iterates over all regions, lists all CloudWatch Logs **log groups** with their **tags** and metadata (retention, size, etc.). Exports a CSV with tags as dynamic columns. |

#### 🔑 IAM (`iam/`)
| Script | Description |
|--------|-------------|
| **read-iam-users.py** | Lists all IAM users with UserName, UserId, Arn, CreateDate, groups, and attached policies. Outputs JSON to the console. |
| **read-iam-users-with-access-keys.py** | Lists IAM users that have **one or more access keys**. For each key it exports: UserName, AccessKeyId, Status, CreateDate, AgeInDays, UserId, UserArn. Generates a CSV and prints a summary (active/inactive) and the oldest key. |
| **read-export-iam.py** | Exports all IAM users with their groups, policies (direct and from groups), and tags (Project, ProjectStatus, ProjectService, ProjectDescription). Generates `users_iam_tags_permisos.csv`. |
| **read-iam-users-without-mfa.py** | Lists IAM users that **do not have MFA** enabled. Exports a CSV with UserName, UserId, Arn, CreateDate, PasswordLastUsed. |
| **read-iam-access-keys-older-than-90-days.py** | Lists IAM access keys **older than 90 days** (configurable) for rotation. Exports a CSV with UserName, AccessKeyId, Status, CreateDate, AgeInDays, UserId, UserArn. |

#### Secrets Manager (`secretsmanager/`)
| Script | Description |
|--------|-------------|
| **read-secrets-manager-inventory.py** | Lists **Secrets Manager** secrets per region (all regions or one via argument). Uses `list_secrets` + `describe_secret` for each (no secret values). CSV includes rotation flags, Lambda rotation ARN, rotation rules (JSON), KMS key, last changed/rotated/accessed, pending deletion, owning service, version count, tags. Prints count of secrets with `RotationEnabled=False`. Run: `python secretsmanager/read-secrets-manager-inventory.py` or `python secretsmanager/read-secrets-manager-inventory.py sa-east-1`. |

#### DynamoDB (`dynamodb/`)
| Script | Description |
|--------|-------------|
| **read-dynamodb-tables-inventory.py** | Lists **DynamoDB tables** per region (all regions or one via argument). Per table: `describe_table` (billing mode, RCU/WCU, size, item count, stream, SSE, GSI/LSI counts, creation time), `describe_time_to_live` (TTL status), `describe_continuous_backups` (PITR). Exports `dynamodb_tables_inventory_<timestamp>.csv`. Prints count with PITR enabled. Run: `python dynamodb/read-dynamodb-tables-inventory.py` or with a region argument. |

#### 🗄️ RDS (`rds/`)
| Script | Description |
|--------|-------------|
| **read-rds-by-region.py** | Lists RDS instances in all regions (or a single region if passed as argument). Exports a CSV with Region, DBInstanceIdentifier, Engine, EngineVersion, DBInstanceClass, DBInstanceStatus, EndpointAddress, EndpointPort, AllocatedStorage, MultiAZ, VpcId, AvailabilityZone, DBInstanceArn. Usage: `python rds/read-rds-by-region.py` or `python rds/read-rds-by-region.py sa-east-1`. |
| **read-rds-public-private.py** | Lists RDS instances in all regions and indicates **public** vs **private** (PubliclyAccessible). Exports a CSV with Region, DBInstanceIdentifier, Accessibility (Public/Private), Engine, status, endpoint, VpcId, etc. Prints count of public and private instances. Optional region filter: `python rds/read-rds-public-private.py sa-east-1`. |

#### 📦 Inventory (`by-region/`)
| Script | Description |
|--------|-------------|
| **list-resources.py** | Regional inventory: set the **`REGION`** constant at the top of the file (default `sa-east-1`). Lists EC2 (instances, volumes, security groups, VPCs, AMIs, snapshots), RDS, Lambda, ECR, S3 buckets in that region, and CloudWatch Logs. Exports `resources_<REGION>_<timestamp>.csv` with Region, Service, ResourceType, ResourceId, Name, Extra. Prints a summary count by service/type. Run: `python by-region/list-resources.py`. |

#### 🌍 Route 53 (`route53/`)
| Script | Description |
|--------|-------------|
| **read-route53-list-zones-and-records.py** | Lists all **hosted zones** and **resource record sets** (DNS records) per zone. Exports two CSVs with the same timestamp: `route53_hosted_zones_*.csv` (zone id, name, record count, private flag) and `route53_record_sets_*.csv` (HostedZoneId, ZoneName, RecordName, Type, TTL, Value). Run: `python route53/read-route53-list-zones-and-records.py`. |

#### 🪣 S3 (root)
| Script | Description |
|--------|-------------|
| **read-s3-tags-by-project-report.py** | Lists S3 buckets that **do not have** the `Project` tag. Gets each bucket’s region and exports `buckets_without_project_tag.csv` with BucketName and Region. |
| **read-s3-public-access-block.py** | Lists **all S3 buckets** with **Block Public Access** settings (or `not_configured` if missing). Exports a CSV with BucketName, Region, the four block flags, status, and **FullyBlocked** (Yes/No). Prints buckets that need review. |

#### 🛡️ Security groups (root)
| Script | Description |
|--------|-------------|
| **read-security-groups.py** | In region `sa-east-1`, lists security groups with **open** rules (ingress or egress with `0.0.0.0/0` or `::/0`). Exports `security_groups_open.csv` with SG ID, name, direction, and CIDR. |

---

### 🗺️ Planned additions
- Automated backup of EC2 instances or EBS volumes, filtered by tags or regions.
- AWS cost reports filtered by resource tags.
- Status and performance checks for other services such as RDS or Lambda.
- Access and permission auditing for IAM configurations.

#### ©️ License
By Agustina Fassina
